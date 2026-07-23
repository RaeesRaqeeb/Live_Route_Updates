# app/jobs/scheduled_scraper.py
import asyncio
import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.route import Route
from app.models.scrape_result import ScrapeResult
from app.services.scraper import ScraperService
from app.services.llm_extractor import LLMExtractor  # wraps your ExtractedRouteInfo LLM call
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


async def get_active_routes(session) -> list[Route]:
    """
    Routes to scrape on schedule. Seed this table manually with the
    major tourist routes (Lahore-Islamabad, Islamabad-Skardu, etc.)
    New routes get added automatically when users search for them
    (see route_discovery.py below).
    """
    result = await session.execute(select(Route).where(Route.is_active == True))
    return result.scalars().all()


from app.schemas.scrape import RawScrapeData
from app.services.llm_extractor import LLMExtractor  # not LLMExtractorService

# app/jobs/scheduled_scraper.py — add this

from app.services.graph_api_service import GraphAPIService

GB_KEYWORDS = ["skardu", "gilgit", "hunza", "kkh", "karakoram"]

def _is_gb_route(route: Route) -> bool:
    combined = f"{route.origin_city} {route.destination_city}".lower()
    return any(k in combined for k in GB_KEYWORDS)


async def scrape_and_store_route(session, scraper: ScraperService, graph_api: GraphAPIService,
                                   extractor: LLMExtractor, route: Route):
    origin, destination = route.origin_city, route.destination_city
    route_query = f"{origin} to {destination}"

    raw_results = []

    # Regular sources (NHMP, SerpAPI, mbasic FB) — always run
    try:
        raw_results.extend(await scraper.scrape_route_news(origin, destination))
    except Exception as e:
        logger.error(f"Scrape failed for {origin}->{destination}: {e}")

    # Your own Page — only relevant for GB/KKH routes
    if _is_gb_route(route):
        try:
            raw_results.extend(await graph_api.fetch_recent_posts(limit=25))
        except Exception as e:
            logger.error(f"Graph API fetch failed for {origin}->{destination}: {e}")

    # ── everything below is UNCHANGED from your existing dedup + extract + store logic ──
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
        if existing.scalar_one_or_none():
            continue

        raw_scrape = RawScrapeData(source=raw["source"], url=raw.get("url", ""), content=content)
        extracted = await extractor.extract_route_info(raw_scrape, route_query)
        if extracted is None:
            continue

        session.add(ScrapeResult(
            route_id=route.id,
            source_name=raw["source"],
            source_url=raw.get("url", ""),
            headline=extracted.headline,
            route_affected=extracted.route_affected or route_query,
            issue_type=extracted.issue_type,
            severity=extracted.severity,
            raw_content=content[:3000],
            summary=extracted.summary,
            content_hash=new_hash,
            is_active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=6),
        ))

    await session.commit()


async def run_scheduled_scrape():
    """
    Entry point called every 30-60 min by the scheduler.
    Processes routes SEQUENTIALLY with delay, not in parallel,
    to respect per-domain rate limits (your RateLimiter already
    handles per-request delay inside ScraperService, this adds
    a per-route gap on top).
    """
    logger.info("=== Scheduled scrape job started ===")
    scraper = ScraperService()
    graph_api = GraphAPIService()
    extractor = LLMExtractor()

    async with AsyncSessionLocal() as session:
        routes = await get_active_routes(session)
        for route in routes:
            await scrape_and_store_route(session, scraper, graph_api, extractor, route)
            await asyncio.sleep(5) # small gap between routes, extra politeness buffer

        # ── Expire old alerts so stale data doesn't show as "current" ──
        await session.execute(
            ScrapeResult.__table__.update()
            .where(ScrapeResult.expires_at < datetime.now(timezone.utc))
            .values(is_active=False)
        )
        await session.commit()

    logger.info("=== Scheduled scrape job finished ===")