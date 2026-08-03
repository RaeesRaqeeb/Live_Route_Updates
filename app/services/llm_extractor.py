import asyncio
from typing import List, Optional

from openai import AsyncOpenAI

from app.core.config import settings
from app.schemas.scrape import ExtractedRouteInfo, RawScrapeData,BatchExtractionResult,BatchExtractedItem
from app.utils.logger import get_logger
from app.utils.text_cleaner import TextCleaner
from app.utils.rate_limiter import groq_limiter

logger = get_logger(__name__)


SINGLE_ITEM_CHAR_LIMIT = 4500

import re
from datetime import datetime
def deduplicate_nhmp_batch(batch: list[dict]) -> list[dict]:
    """
    For NHMP records (source starts with '__nhmp__'), keep only the single
    latest record per unique content payload, determined by 'post_created_at'.
    Records older than 7 days from today are discarded as stale.
    All other source types are passed through unchanged.
    """
    from datetime import datetime, timezone, timedelta

    def is_nhmp(rec: dict) -> bool:
        src = rec.get("source") or ""
        return src.startswith("__nhmp__")

    now = datetime.now(timezone.utc)
    max_age = timedelta(days=7)

    best: dict[str, dict] = {}  # key = content → best record so far

    for rec in batch:
        if not is_nhmp(rec):
            continue
        key = (rec.get("content") or "").strip()
        if not key:
            continue
        ts_str = rec.get("post_created_at") or ""
        try:
            ts = datetime.fromisoformat(ts_str)
            # Make timezone-aware if naive
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            ts = datetime.min.replace(tzinfo=timezone.utc)

        # ── Staleness check: skip if older than 7 days ──
        if (now - ts) > max_age:
            logger.debug(
                f"deduplicate_nhmp_batch: dropping stale record "
                f"{rec.get('source')} (age={(now - ts).days} days)"
            )
            continue

        if key not in best or ts > best[key]["_ts"]:
            best[key] = {**rec, "_ts": ts}

    out: list[dict] = []
    seen_keys: set[str] = set()

    for rec in batch:
        if not is_nhmp(rec):
            out.append(rec)
            continue
        key = (rec.get("content") or "").strip()
        winner = best.get(key)
        if (
                winner
                and rec.get("post_created_at") == winner.get("post_created_at")
                and key not in seen_keys
        ):
            seen_keys.add(key)
            out.append({k: v for k, v in winner.items() if k != "_ts"})

    return out

def filter_latest_nhmp_closure(content: str) -> str:
    """
    NHMP content can arrive as several closure entries concatenated together
    (e.g. multiple records for the same route pasted back to back, separated
    by blank lines). We only want the most recent one in the LLM prompt so
    older/superseded closures don't get treated as current.

    Each block's header line ([SRC_N] / timestamp / source) is stripped before
    comparison so that blocks with identical route/alert data but different
    injected metadata are still recognised as duplicates. Only the first
    (latest) unique block is returned.
    """
    if not content:
        return ""

    _HEADER_RE = re.compile(r'^\[SRC_\d+\]\s*\(time:[^)]*\)\s*\(source:[^)]*\)\s*', re.MULTILINE)

    seen: set[str] = set()
    unique_blocks: list[str] = []

    for block in content.split("\n\n"):
        stripped = block.strip()
        if not stripped:
            continue
        # Normalise: remove injected header so duplicate payloads are detected
        normalised = _HEADER_RE.sub("", stripped).strip()
        if normalised and normalised not in seen:
            seen.add(normalised)
            unique_blocks.append(stripped)   # keep original (with header) for output

    return unique_blocks[0] if unique_blocks else content.strip()


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
            {cleaned_content[:SINGLE_ITEM_CHAR_LIMIT]}
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
    ) -> tuple[List[tuple[dict, "BatchExtractedItem"]], dict]:
        """
        Extract structured data from all scraped results in a SINGLE Groq call.
        """
        valid_results = [
            r for r in scraped_results
            if r.get("scrape_success") and r.get("content")
        ]

        if not valid_results:
            return [], {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        # MAX_ITEMS_PER_BATCH = 10
        # PER_ITEM_CHAR_LIMIT = 1200

        # Fix: MAX_ITEMS_PER_BATCH was declared but never applied, so a
        # data-rich route (e.g. GB/KKH) could still blow past Groq's
        # context/rate limits in a single call. Slice and log if we drop items.
        batch = valid_results
        # if len(valid_results) > MAX_ITEMS_PER_BATCH:
        #     logger.warning(
        #         f"batch_extract: {len(valid_results)} valid items for '{route_query}', "
        #         f"truncating to {MAX_ITEMS_PER_BATCH} (TODO: chunk into multiple batches instead of dropping)"
        #     )
        print("*"*20)
        print("batch from database:",batch)
        print("*"*20)

        blocks = []
        source_map = {}

        batch = deduplicate_nhmp_batch(batch)   # ← add this

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
        print("*"*20)
        print("Cleaned Data:",blocks)
        print("*"*20)
        # exit()
        if not blocks:
            return [], {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

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
            print("*"*20)
            print("Parsed Data:",parsed)
            print("*"*20)
            # exit()
            extracted = []
            for item in parsed.items:
                if not item.is_route_related:
                    continue
                src = source_map.get(item.source_id)
                if src is None:
                    logger.warning(f"Batch extraction returned unknown source_id: {item.source_id}")
                    continue
                extracted.append((src, item))

            logger.info(
                f"Groq batch-extracted {len(extracted)} relevant items from {len(blocks)} sources "
                f"(1 API call, {usage['total_tokens']} tokens)"
            )

            # print("*"*20)
            # print("Extracted summaru:",extracted)
            # print("*"*20)

            return extracted, usage

        except Exception as e:
            logger.error(f"Groq batch extraction error: {e}")
            return [], {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}