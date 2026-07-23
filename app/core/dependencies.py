# app/core/dependencies.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.cache_service import CacheService
from app.services.scraper import ScraperService
from app.services.weather_service import WeatherService
from app.services.rag_service import RAGService
from app.repositories.route_repo import RouteRepository
from app.repositories.scrape_repo import ScrapeRepository
from app.repositories.query_repo import QueryRepository


# ── DB Session ────────────────────────────────────────────────────────────────
async def get_database() -> AsyncSession:
    async for session in get_db():
        yield session


# ── Service Dependencies ──────────────────────────────────────────────────────
def get_cache_service() -> CacheService:
    return CacheService()


def get_scraper_service() -> ScraperService:
    return ScraperService()


def get_weather_service() -> WeatherService:
    return WeatherService()


def get_rag_service() -> RAGService:
    return RAGService()


# ── Repository Dependencies ───────────────────────────────────────────────────
def get_route_repo(db: AsyncSession = Depends(get_database)) -> RouteRepository:
    return RouteRepository(db)


def get_scrape_repo(db: AsyncSession = Depends(get_database)) -> ScrapeRepository:
    return ScrapeRepository(db)


def get_query_repo(db: AsyncSession = Depends(get_database)) -> QueryRepository:
    return QueryRepository(db)