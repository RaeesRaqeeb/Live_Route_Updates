# app/services/route_pipeline.py
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.route import Route
from app.models.scrape_result import ScrapeResult
from app.schemas.scrape import RawScrapeData
from app.services.scraper import ScraperService
from app.services.graph_api_service import GraphAPIService
from app.services.llm_extractor import LLMExtractor
from app.utils.logger import get_logger

logger = get_logger(__name__)

GB_KEYWORDS = ["skardu", "gilgit", "hunza", "kkh", "karakoram", "astore", "northern"]


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def is_gb_route(origin: str, destination: str) -> bool:
    combined = f"{destination}".lower()
    return any(k in combined for k in GB_KEYWORDS)

# app/services/route_pipeline.py — fetch_raw_sources, revised

async def fetch_raw_sources(origin, destination, scraper, graph_api):
    results = []

    if is_gb_route(origin, destination):
        try:
            fb_results = await graph_api.fetch_recent_posts(limit=5)
            results.extend(fb_results)
        except Exception as e:
            logger.error(f"Graph API fetch failed for {origin}->{destination}: {e}")

        # Always also try NHMP + SerpAPI for GB routes as a fallback,
        # not just when the FB page fails — since it's a genuine safety alert path.
        try:
            results.extend(await scraper.serpapi(origin, destination))
        except Exception as e:
            logger.error(f"Scrape fallback failed for {origin}->{destination}: {e}")
    else:
        try:
            results.extend(await scraper.scrape_route_news(origin, destination))
        except Exception as e:
            logger.error(f"Scrape failed for {origin}->{destination}: {e}")

    return results

def _row_to_dict(row: ScrapeResult) -> Dict[str, Any]:
    """Shape matches what RAGService._normalize_docs expects (already-structured)."""
    return {
        "source": row.source_name,
        "url": row.source_url,
        "content": row.summary or row.raw_content,
        "scrape_success": True,
        "error": None,
        "from_db": True,  # tells RAG: skip re-extraction, already structured
        "headline": row.headline,
        "issue_type": row.issue_type,
        "severity": row.severity,
        "route_affected": row.route_affected,
        "summary": row.summary,
        "created_at": row.created_at,
    }

async def scrape_extract_and_store(
    session: AsyncSession,
    route: Route,
    scraper: ScraperService,
    graph_api: GraphAPIService,
    extractor: LLMExtractor,
    commit: bool = True,
) -> List[Dict[str, Any]]:
    origin, destination = route.origin_city, route.destination_city
    route_query = f"{origin} to {destination}"

    try:
        raw_results = await fetch_raw_sources(origin, destination, scraper, graph_api)
    except Exception as e:
        logger.error(f"There is some issue with getting data: {e}")
        raw_results = []

    structured_items: List[Dict[str, Any]] = []
    to_extract: List[dict] = []
    hash_by_source_url: Dict[str, str] = {}  # keyed by (source,url) since we can't index-map anymore

    for raw in raw_results:
        if not raw.get("scrape_success") or not raw.get("content"):
            continue

        content = raw["content"]
        new_hash = _hash_content(content)

        existing = await session.execute(
            select(ScrapeResult).where(
                ScrapeResult.route_id == route.id,
                ScrapeResult.source_name == raw["source"],
                ScrapeResult.content_hash == new_hash,
            )
        )
        existing_row = existing.scalar_one_or_none()
        if existing_row:
            logger.info(f"[skip] {raw['source']} unchanged for {origin}->{destination}")
            if existing_row.is_active:
                structured_items.append(_row_to_dict(existing_row))
            continue

        min_len = 15 if raw["source"] == "own_fb_page" else 30
        if len(content.strip()) < min_len:
            continue

        key = f"{raw['source']}::{raw.get('url','')}"
        hash_by_source_url[key] = new_hash
        to_extract.append(raw)

    # ── ONE Groq call covers every new/changed item on this route ──
    if to_extract:
        extracted_pairs = await extractor.batch_extract(to_extract, route_query)

        for src, item in extracted_pairs:
            content = src["content"]
            key = f"{src['source']}::{src.get('url','')}"
            new_hash = hash_by_source_url[key]

            result_row = ScrapeResult(
                route_id=route.id,
                source_name=src["source"],
                source_url=src.get("url", ""),
                headline=item.headline,
                route_affected=item.route_affected or route_query,
                issue_type=item.issue_type,
                severity=item.severity,
                raw_content=content[:3000],
                summary=item.summary,
                content_hash=new_hash,
                is_active=True,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=6),
            )
            session.add(result_row)
            await session.flush()
            structured_items.append(_row_to_dict(result_row))

    if commit:
        await session.commit()

    return structured_items