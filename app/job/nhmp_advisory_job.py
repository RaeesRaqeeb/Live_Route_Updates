# app/job/nhmp_advisory_job.py
import asyncio
from datetime import datetime, timezone, timedelta

from app.core.database import AsyncSessionLocal
from app.services.nhmp_page_scraper import fetch_nhmp_advisory_html, parse_nhmp_advisory_page
from app.services.route_discovery import get_or_create_route
from app.services.llm_extractor import LLMExtractor
from app.models.scrape_result import ScrapeResult
from app.utils.logger import get_logger
from sqlalchemy import select
import hashlib

logger = get_logger(__name__)

DELAY_BETWEEN_SECTORS_SECONDS = 60  # pacing, per your requirement


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _sector_to_text(sector: dict) -> str:
    lines = [f"{a['text']}" for a in sector["alerts"]]
    return "\n".join(lines) if lines else "Road & Weather Clear"


async def run_nhmp_advisory_scrape():
    logger.info("=== NHMP full-page advisory scrape started ===")
    extractor = LLMExtractor()

    try:
        html = await fetch_nhmp_advisory_html()
    except Exception as e:
        logger.error(f"NHMP page fetch failed: {e}")
        return

    sectors = parse_nhmp_advisory_page(html)
    if not sectors:
        logger.warning("No sectors parsed — skipping this run")
        return

    async with AsyncSessionLocal() as session:
        for i, sector in enumerate(sectors):
            content = _sector_to_text(sector)
            new_hash = _hash_content(content)

            route = await get_or_create_route(session, sector["origin"], sector["destination"])

            existing = await session.execute(
                select(ScrapeResult).where(
                    ScrapeResult.route_id == route.id,
                    ScrapeResult.source_name == "NHMP_PAGE",
                    ScrapeResult.content_hash == new_hash,
                    )
            )
            if existing.scalar_one_or_none():
                logger.info(f"[skip] NHMP_PAGE unchanged for {sector['sector_name']}")
                continue  # no LLM call needed, no delay needed — content identical to last run

            try:
                extracted_pairs, usage = await extractor.batch_extract(
                    [{
                        "source": "NHMP_PAGE",
                        "url": "https://beta.nhmp.gov.pk/TA/Public/ViewTravel.aspx",
                        "content": content,
                        "scrape_success": True,
                    }],
                    route_query=f"{sector['origin']} to {sector['destination']}",
                )
            except Exception as e:
                logger.error(f"Extraction failed for {sector['sector_name']}: {e}")
                extracted_pairs = []

            for src, item in extracted_pairs:
                row = ScrapeResult(
                    route_id=route.id,
                    source_name="NHMP_PAGE",
                    source_url=src["url"],
                    headline=item.headline,
                    route_affected=item.route_affected or f"{sector['origin']} to {sector['destination']}",
                    issue_type=item.issue_type,
                    severity=item.severity,
                    raw_content=content[:3000],
                    summary=item.summary,
                    content_hash=new_hash,
                    is_active=True,
                    expires_at=datetime.now(timezone.utc) + timedelta(minutes=45),  # matches scrape interval
                )
                session.add(row)

            await session.commit()
            logger.info(f"[{i+1}/{len(sectors)}] stored {sector['sector_name']} ({sector['origin']}->{sector['destination']})")

            if i < len(sectors) - 1:
                await asyncio.sleep(DELAY_BETWEEN_SECTORS_SECONDS)

    logger.info("=== NHMP full-page advisory scrape finished ===")