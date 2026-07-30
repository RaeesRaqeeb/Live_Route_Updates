# app/services/rag_service.py
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

from app.core.config import settings
from app.schemas.scrape import ExtractedRouteInfo, IssueTypeEnum, SeverityEnum
from app.schemas.response import RouteAlert, AlertLevel, WeatherInfo
from app.utils.logger import get_logger
from app.utils.rate_limiter import groq_limiter
from openai import AsyncOpenAI

logger = get_logger(__name__)


@dataclass
class RAGAnswer:
    summary: str
    alert_level: AlertLevel
    alerts: List[RouteAlert]


class RAGService:
    def __init__(self):
        # Groq uses the OpenAI SDK standard
        self.client = AsyncOpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
            timeout=20.0,
        )
        self.model = settings.GROQ_MODEL

    def _determine_alert_level(self, items: List[dict]) -> AlertLevel:
        """items: list of dicts with a 'severity' key (lowercase string)."""
        if not items:
            return AlertLevel.UNKNOWN

        severities = [i["severity"].lower() for i in items]
        if "high" in severities:
            return AlertLevel.DANGER
        elif "medium" in severities:
            return AlertLevel.CAUTION
        elif "low" in severities:
            return AlertLevel.SAFE
        return AlertLevel.UNKNOWN

    def _build_context(
        self,
        items: List[dict],
        weather_origin: Optional[WeatherInfo],
        weather_dest: Optional[WeatherInfo],
    ) -> str:
        context_parts = []

        if weather_origin:
            context_parts.append(
                f"WEATHER at {weather_origin.city}: "
                f"{weather_origin.temperature_celsius}°C, "
                f"{weather_origin.condition}, "
                f"Humidity: {weather_origin.humidity_percent}%, "
                f"Wind: {weather_origin.wind_speed_kmh} km/h. "
                f"Advisory: {weather_origin.advisory}"
            )

        if weather_dest:
            context_parts.append(
                f"WEATHER at {weather_dest.city}: "
                f"{weather_dest.temperature_celsius}°C, "
                f"{weather_dest.condition}. "
                f"Advisory: {weather_dest.advisory}"
            )

        for item in items:
            context_parts.append(
                f"[{item['severity'].upper()} - {item['issue_type']}] "
                f"{item['headline']}. "
                f"Route: {item.get('route_affected') or 'Not specified'}. "
                f"{item['summary']}"
            )

        return "\n\n".join(context_parts) if context_parts else "No specific alerts found."

    async def _generate_summary(self, prompt: str) -> str:
        try:
            await groq_limiter.acquire()
        except Exception as e:
            logger.info("There is some issue here:",str(e))
            
        print("WE ARE REACHING HERE OR NOT?")
        # Updated to use OpenAI Chat Completions format for Groq
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a concise Pakistan travel safety assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=600,
        )
        
        text = response.choices[0].message.content.strip() if response.choices else ""
        if not text:
            raise ValueError("Empty response from Groq")
        return text

    def _normalize_docs(self, scraped_docs: List[dict]) -> List[dict]:
        """
        Convert already-structured DB docs into the common dict shape
        used by _build_context / _determine_alert_level / alert building.
        Raw (non-DB) docs are left out here — they get extracted separately.
        """
        normalized = []
        for doc in scraped_docs:
            if doc.get("from_db"):
                normalized.append({
                    "headline": doc["headline"],
                    "issue_type": doc["issue_type"].value if hasattr(doc["issue_type"], "value") else doc["issue_type"],
                    "severity": doc["severity"].value if hasattr(doc["severity"], "value") else doc["severity"],
                    "route_affected": doc.get("route_affected"),
                    "summary": doc["summary"],
                    "source": doc["source"],
                    "source_url": doc.get("url", ""),
                    "scraped_at": doc.get("created_at", datetime.utcnow()),
                })
        return normalized
    async def answer_route_query(
            self,
            query: str,
            scraped_docs: List[dict],
            weather_origin: Optional[WeatherInfo] = None,
            weather_destination: Optional[WeatherInfo] = None,
            data_fetch_failed: bool = False
    ) -> RAGAnswer:
        """
        Build final answer using extracted data + weather.
        scraped_docs may be a MIX of:
          - DB-sourced dicts (from_db=True) — already structured, skip LLM extraction
          - raw scraped dicts (from_db missing/False) — need LLM extraction
        """
        db_docs = [d for d in scraped_docs if d.get("from_db")]
        raw_docs = [d for d in scraped_docs if not d.get("from_db")]
        logger.info(f"RAG input split: {len(db_docs)} from DB (skip extraction), {len(raw_docs)} raw (needs extraction)")

        # ── Step 1: only run extraction on genuinely raw docs ──
        extracted_from_raw = []
        if raw_docs:
            from app.services.llm_extractor import LLMExtractor
            extractor = LLMExtractor()

            extracted_items = await extractor.batch_extract(raw_docs, query)

            # Unpack the tuple into 'src_dict' and 'item_model'
            for src_dict, item_model in extracted_items:
                extracted_from_raw.append({
                    "headline": item_model.headline,
                    "issue_type": item_model.issue_type.value,
                    "severity": item_model.severity.value,
                    "route_affected": item_model.route_affected,
                    "summary": item_model.summary,
                    "corridor_fallback": item_model.corridor_fallback,
                    # Pull source metadata directly from the source dictionary
                    "source": src_dict.get("source", "scraped"),
                    "source_url": src_dict.get("url", ""),
                    "scraped_at": datetime.utcnow(),
                })

        all_items = self._normalize_docs(db_docs) + extracted_from_raw

        # ── Step 2: Determine alert level ──
        alert_level = self._determine_alert_level(all_items)

        # ── Step 3: Build context ──
        context = self._build_context(all_items, weather_origin, weather_destination)

        # ── Guard: skip LLM narrative call if nothing meaningful ──
        has_weather = weather_origin is not None or weather_destination is not None
        has_alerts = len(all_items) > 0

        # Check if ANY of the data relied on a corridor fallback
        has_corridor_fallback = any(i.get("corridor_fallback", False) for i in all_items)

        if not has_alerts and not data_fetch_failed:
            # Genuinely queried sources successfully and found nothing — safe to say "no alerts"
            pass  # Proceed to generate normal summary
        elif not has_alerts and data_fetch_failed:
            return RAGAnswer(
                summary=(
                    f"We couldn't retrieve current road/route data for {query} right now "
                    f"due to a temporary data source issue. This does NOT confirm the route "
                    f"is clear — please check NHMP (nhmp.gov.pk) or PMD directly before traveling."
                ),
                alert_level=AlertLevel.UNKNOWN,
                alerts=[],
            )

        # ── Step 4: Generate final narrative summary ──

        # Dynamically inject the caveat instruction if using fallback data
        fallback_instruction = ""
        if has_corridor_fallback:
            fallback_instruction = (
                "\nCRITICAL INSTRUCTION FOR THIS ROUTE:\n"
                "We do not have direct reports for this exact route. The alerts in the CURRENT INFORMATION "
                "are based on the broader highway/corridor. You MUST explicitly caveat your summary "
                "(e.g., 'While there are no direct reports for your exact route, the broader corridor shows...'). "
                "Do NOT present these alerts as route-specific certainty or falsely specific facts.\n"
            )

        prompt = f"""
                    You are a Pakistan travel assistant providing route intelligence.
        
                    USER'S ROUTE: {query}
                    {fallback_instruction}
                    CURRENT INFORMATION:
                    {context}
        
                    Write a concise, helpful travel briefing (3-5 sentences) for this route covering:
                    1. Overall road safety status
                    2. Key weather conditions
                    3. Any active alerts or issues
                    4. A practical recommendation for the traveler
        
                    Be direct and specific. Mention city/highway names. Write in English.
                    If no issues found, confirm the route appears clear.
                    """.strip()

        try:
            summary = await self._generate_summary(prompt)
        except Exception as e:
            logger.error(f"RAG summary generation error: {e}")
            summary = f"Route information for {query}. {len(all_items)} alert(s) found."

        # ── Step 5: Build RouteAlert list (each with its own correct URL) ──
        alerts = [
            RouteAlert(
                headline=i["headline"],
                issue_type=i["issue_type"],
                severity=i["severity"],
                route_affected=i["route_affected"],
                summary=i["summary"],
                source=i["source"],
                source_url=i["source_url"],
                scraped_at=i["scraped_at"],
            )
            for i in all_items
        ]

        return RAGAnswer(summary=summary, alert_level=alert_level, alerts=alerts)