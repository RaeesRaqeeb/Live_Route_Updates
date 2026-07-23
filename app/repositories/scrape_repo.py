# app/repositories/scrape_repo.py
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.scrape_result import ScrapeResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ScrapeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> ScrapeResult:
        """Save a scraped result to the database."""
        scrape = ScrapeResult(**data)
        self.db.add(scrape)
        await self.db.flush()
        await self.db.refresh(scrape)
        return scrape

    async def bulk_create(self, items: List[dict]) -> List[ScrapeResult]:
        """Save multiple scraped results at once."""
        scrapes = [ScrapeResult(**item) for item in items]
        self.db.add_all(scrapes)
        await self.db.flush()
        logger.info(f"Bulk saved {len(scrapes)} scrape results")
        return scrapes

    async def get_recent_by_route(
        self,
        route_id: int,
        limit: int = 10,
    ) -> List[ScrapeResult]:
        """Fetch the most recent alerts for a route."""
        stmt = (
            select(ScrapeResult)
            .where(
                ScrapeResult.route_id == route_id,
                ScrapeResult.is_active == True,
            )
            .order_by(desc(ScrapeResult.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_source(self, source_name: str, limit: int = 20) -> List[ScrapeResult]:
        stmt = (
            select(ScrapeResult)
            .where(ScrapeResult.source_name == source_name)
            .order_by(desc(ScrapeResult.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def deactivate_old(self, hours: int = 24) -> int:
        """Mark scrape results older than N hours as inactive."""
        from sqlalchemy import update
        from datetime import datetime, timedelta

        cutoff = datetime.utcnow() - timedelta(hours=hours)
        stmt = (
            update(ScrapeResult)
            .where(ScrapeResult.created_at < cutoff)
            .values(is_active=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount