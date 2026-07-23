import asyncio
from typing import List, Optional

from openai import AsyncOpenAI

from app.core.config import settings
from app.schemas.scrape import ExtractedRouteInfo, RawScrapeData
from app.utils.logger import get_logger
from app.utils.text_cleaner import TextCleaner
from app.utils.rate_limiter import groq_limiter

logger = get_logger(__name__)


class LLMExtractor:
    def __init__(self, max_concurrency: int = 8):  # Groq handles higher concurrency well
        self.client = AsyncOpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
        )
        self.model = settings.GROQ_MODEL
        self.cleaner = TextCleaner()
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def extract_route_info(
        self,
        raw_data: RawScrapeData,
        route_query: str,
    ) -> Optional[ExtractedRouteInfo]:
        """
        Use Groq + Llama to extract structured route information.
        Uses structured outputs via Pydantic model (very similar to Gemini).
        """
        cleaned_content = self.cleaner.clean(raw_data.content)
        if not cleaned_content or len(cleaned_content) < 10:
            return None

        prompt = f"""From the text below, determine if it contains any travel/route issues in Pakistan:
- road conditions, accidents, blockages, weather affecting roads, construction, security alerts.

Route the user cares about: {route_query}
Source: {raw_data.source}

Text:
{cleaned_content[:4500]}
"""

        try:
            await groq_limiter.acquire()
            async with self.semaphore:
                response = await self.client.beta.chat.completions.parse(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a Pakistan travel intelligence assistant. "
                                "Analyze the provided text and respond with structured data "
                                "following the given schema exactly. Be factual and concise."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.0,      # Very deterministic for extraction
                    max_tokens=800,
                    response_format=ExtractedRouteInfo,   # Pydantic model → structured output
                )

            if not response.choices or not response.choices[0].message.parsed:
                return None

            extracted: ExtractedRouteInfo = response.choices[0].message.parsed

            if not extracted.is_route_related:
                return None

            return extracted

        except Exception as e:
            logger.error(f"Groq extraction error: {e}")
            return None

    async def batch_extract(
        self,
        scraped_results: List[dict],
        route_query: str,
    ) -> List[ExtractedRouteInfo]:
        """
        Extract structured data from all scraped results in parallel.
        """
        tasks = []

        for result in scraped_results:
            if result.get("scrape_success") and result.get("content"):
                raw = RawScrapeData(
                    source=result["source"],
                    url=result["url"],
                    content=result["content"],
                )
                tasks.append(self.extract_route_info(raw, route_query))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        extracted = []
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"Extraction task failed: {r}")
            elif r is not None:
                extracted.append(r)

        logger.info(f"Groq extracted {len(extracted)} relevant items")
        return extracted