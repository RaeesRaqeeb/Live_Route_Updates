import asyncio
from typing import List, Optional

from openai import AsyncOpenAI

from app.core.config import settings
from app.schemas.scrape import ExtractedRouteInfo, RawScrapeData,BatchExtractionResult,BatchExtractedItem
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
    ) -> List[tuple[dict, ExtractedRouteInfo]]:
        """
        Extract structured data from all scraped results in a SINGLE Groq call.
        """
        valid_results = [
            r for r in scraped_results
            if r.get("scrape_success") and r.get("content")
        ]

        if not valid_results:
            return []

        # Guard against context blowup on GB routes with many sources
        MAX_ITEMS_PER_BATCH = 12
        PER_ITEM_CHAR_LIMIT = 1200  # smaller than before since multiple share one prompt

        batch = valid_results[:MAX_ITEMS_PER_BATCH]
        if len(valid_results) > MAX_ITEMS_PER_BATCH:
            logger.warning(
                f"{len(valid_results)} items scraped, only extracting first {MAX_ITEMS_PER_BATCH}"
            )

        # Build labeled, source-tagged blocks
        # print("*"*20)
        # print("Extracted information:",batch)
        # print("*"*20)
        # exit()
        blocks = []
        source_map = {}  # source_id -> original result dict
        for i, result in enumerate(batch):
            # print("Results:",result)
            # exit()
            cleaned = self.cleaner.clean(result["content"])
            if not cleaned or len(cleaned) < 10:
                continue
            source_id = f"SRC_{i}"
            source_map[source_id] = result
            
            # Safely get the post creation time, default to "Unknown time" if missing
            post_time = result.get("post_created_at", "Unknown time")
            
            blocks.append(
                f"[{source_id}] (time: {post_time}) (source: {result['source']})\n{cleaned[:PER_ITEM_CHAR_LIMIT]}"
            )
        # print("*"*20)
        # print("Extracted information:",blocks)
        # print("*"*20)
        # exit()
        if not blocks:
            return []

        prompt = f"""Below are {len(blocks)} separate text snippets scraped from different sources about travel conditions in Pakistan.

    Route the user cares about: {route_query}

    For EACH snippet, determine if it contains travel/route issues (road conditions, accidents, blockages, weather affecting roads, construction, security alerts according to time latest news be prefered). Return one item per snippet in the `items` list, using its exact source_id label, even if is_route_related is false.

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
                                "with structured data for every snippet, following the schema exactly."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.0,
                    max_tokens=min(300 * len(blocks) + 300, 6000),
                    response_format=BatchExtractionResult,
                )

            if not response.choices or not response.choices[0].message.parsed:
                return []

            parsed: BatchExtractionResult = response.choices[0].message.parsed

            extracted = []
            for item in parsed.items:
                if not item.is_route_related:
                    continue
                src = source_map.get(item.source_id)
                if src is None:
                    logger.warning(f"Batch extraction returned unknown source_id: {item.source_id}")
                    continue
                extracted.append((src, item))   # ← pair, not bare item

            logger.info(f"Groq batch-extracted {len(extracted)} relevant items from {len(blocks)} sources (1 API call)")
            return extracted

        except Exception as e:
            logger.error(f"Groq batch extraction error: {e}")
            return []