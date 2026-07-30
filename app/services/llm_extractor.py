import asyncio
from typing import List, Optional

from openai import AsyncOpenAI

from app.core.config import settings
from app.schemas.scrape import ExtractedRouteInfo, RawScrapeData,BatchExtractionResult,BatchExtractedItem
from app.utils.logger import get_logger
from app.utils.text_cleaner import TextCleaner
from app.utils.rate_limiter import groq_limiter

logger = get_logger(__name__)
import json

import json
import json
from datetime import datetime





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
    ) -> tuple[List[tuple[dict, ExtractedRouteInfo]], dict]: # Updated type hint
        """
        Extract structured data from all scraped results in a SINGLE Groq call.
        """
        valid_results = [
            r for r in scraped_results
            if r.get("scrape_success") and r.get("content")
        ]

        if not valid_results:
            return [], {} # FIXED: Return 2 values

        MAX_ITEMS_PER_BATCH = 10
        PER_ITEM_CHAR_LIMIT = 1200

        batch = valid_results

        blocks = []
        source_map = {}

        for i, result in enumerate(batch):
            if result["source"] == "NHMP_API":
                cleaned = filter_latest_nhmp_closure(result["content"])
            else:
                cleaned = self.cleaner.clean(result["content"])

            if not cleaned or len(cleaned) < 10:
                continue

            source_id = f"SRC_{i}"
            source_map[source_id] = result
            post_time = result.get("post_created_at", "Unknown time")

            blocks.append(
                f"[{source_id}] (time: {post_time}) (source: {result['source']})\n{cleaned}"
            )

        if not blocks:
            return [], {} # FIXED: Return 2 values

        prompt = f"""Below are {len(blocks)} separate text snippets scraped from different sources about travel conditions in Pakistan.
    
        Route the user cares about: {route_query}
    
        For EACH snippet, determine if it contains travel/route issues (road conditions, accidents, blockages, weather affecting roads, construction, lane close (true/false) security alerts according to time latest news be prefered). Return one item per snippet in the `items` list, using its exact source_id label, even if is_route_related is false.
    
        {chr(10).join(blocks)}
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
                                "Analyze each labeled text snippet independently and respond "
                                "with structured data for every snippet, following the schema exactly. "
                                "CRITICAL: Keep 'summary' fields incredibly brief (maximum 15 words per snippet)."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.0,
                    max_tokens=5000,
                    response_format=BatchExtractionResult,
                )

            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            }

            if not response.choices or not response.choices[0].message.parsed:
                return [], usage # FIXED: Return 2 values

            parsed: BatchExtractionResult = response.choices[0].message.parsed

            extracted = []
            logger.info(
                f"Groq batch-extracted {len(extracted)} relevant items from {len(blocks)} sources "
                f"(1 API call, {usage['total_tokens']} tokens)"
            )
            for item in parsed.items:
                if not item.is_route_related:
                    continue
                src = source_map.get(item.source_id)
                if src is None:
                    logger.warning(f"Batch extraction returned unknown source_id: {item.source_id}")
                    continue
                extracted.append((src, item))

            logger.info(f"Groq batch-extracted {len(extracted)} relevant items from {len(blocks)} sources (1 API call)")
            return extracted, usage # Already correct

        except Exception as e:
            logger.error(f"Groq batch extraction error: {e}")
            return [], {} # FIXED: Return 2 values