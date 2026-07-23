# app/repositories/route_repo.py
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.route import Route
from app.schemas.route import RouteCreate, RouteUpdate
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RouteRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: RouteCreate) -> Route:
        """Insert a new route into the database."""
        route = Route(**data.model_dump())
        self.db.add(route)
        await self.db.flush()
        await self.db.refresh(route)
        logger.info(f"Created route: {route.origin_city} → {route.destination_city}")
        return route

    async def get_by_id(self, route_id: int) -> Optional[Route]:
        result = await self.db.execute(select(Route).where(Route.id == route_id))
        return result.scalar_one_or_none()

    async def get_by_cities(
        self, origin: str, destination: str
    ) -> Optional[Route]:
        """Find route by origin and destination cities (case-insensitive)."""
        stmt = select(Route).where(
            and_(
                Route.origin_city.ilike(origin),
                Route.destination_city.ilike(destination),
                Route.is_active == True,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_active(self) -> List[Route]:
        """Fetch all active routes."""
        result = await self.db.execute(
            select(Route).where(Route.is_active == True)
        )
        return list(result.scalars().all())

    async def update(self, route_id: int, data: RouteUpdate) -> Optional[Route]:
        route = await self.get_by_id(route_id)
        if not route:
            return None
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(route, field, value)
        await self.db.flush()
        await self.db.refresh(route)
        return route

    async def delete(self, route_id: int) -> bool:
        route = await self.get_by_id(route_id)
        if not route:
            return False
        route.is_active = False   # Soft delete
        await self.db.flush()
        return True