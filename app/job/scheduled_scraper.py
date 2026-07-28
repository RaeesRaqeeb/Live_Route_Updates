# app/jobs/scheduled_scraper.py
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.route import Route
from app.models.scrape_result import ScrapeResult
from app.services.scraper import ScraperService
from app.services.graph_api_service import GraphAPIService
from app.services.llm_extractor import LLMExtractor
from app.services.route_pipeline import scrape_extract_and_store
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def get_active_routes(session) -> list[Route]:
    result = await session.execute(select(Route).where(Route.is_active == True))
    return result.scalars().all()


async def run_scheduled_scrape():
    logger.info("=== Scheduled scrape job started ===")
    scraper = ScraperService()
    graph_api = GraphAPIService()
    extractor = LLMExtractor()

    async with AsyncSessionLocal() as session:
        routes = await get_active_routes(session)
        logger.info(f"Scraping {len(routes)} active routes")

        for route in routes:
            try:
                await scrape_extract_and_store(session, route, scraper, graph_api, extractor)
            except Exception as e:
                logger.error(f"Pipeline failed for route {route.id} ({route.origin_city}->{route.destination_city}): {e}")
            await asyncio.sleep(5)  # politeness gap between routes

        # Expire stale alerts
        await session.execute(
            ScrapeResult.__table__.update()
            .where(ScrapeResult.expires_at < datetime.now(timezone.utc))
            .values(is_active=False)
        )
        await session.commit()

    logger.info("=== Scheduled scrape job finished ===")