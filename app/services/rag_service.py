# app/services/rag_service.py
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

from google import genai
from google.genai import types

from app.core.config import settings
from app.schemas.scrape import ExtractedRouteInfo, IssueTypeEnum, SeverityEnum
from app.schemas.response import RouteAlert, AlertLevel, WeatherInfo
from app.utils.logger import get_logger
from app.utils.rate_limiter import groq_limiter

logger = get_logger(__name__)


@dataclass
class RAGAnswer:
    summary: str
    alert_level: AlertLevel
    alerts: List[RouteAlert]


class RAGService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = settings.GEMINI_ANSWER_MODEL

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
        config = types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=600,
            system_instruction="You are a concise Pakistan travel safety assistant.",
        )
        await groq_limiter.acquire()
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        text = (response.text or "").strip()
        if not text:
            raise ValueError("Empty response from Gemini")
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
            for item in extracted_items:
                extracted_from_raw.append({
                    "headline": item.headline,
                    "issue_type": item.issue_type.value,
                    "severity": item.severity.value,
                    "route_affected": item.route_affected,
                    "summary": item.summary,
                    "source": getattr(item, "source", "scraped"),
                    "source_url": getattr(item, "source_url", ""),
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

        if not has_weather and not has_alerts:
            logger.info(f"Skipping summary call — no data available for '{query}'")
            return RAGAnswer(
                summary=(
                    f"No verified route alerts or weather data are currently available "
                    f"for {query}. Please check official sources like NHMP or PMD directly."
                ),
                alert_level=AlertLevel.UNKNOWN,
                alerts=[],
            )

        # ── Step 4: Generate final narrative summary ──
        prompt = f"""
                    You are a Pakistan travel assistant providing route intelligence.

                    USER'S ROUTE: {query}

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