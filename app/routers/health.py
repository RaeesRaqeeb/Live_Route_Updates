# app/routers/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.dependencies import get_database
from app.core.config import settings
import redis.asyncio as aioredis

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check(db: AsyncSession = Depends(get_database)):
    """
    Full system health check.
    Verifies: API, PostgreSQL, Redis connectivity.
    """
    status = {
        "app": "ok",
        "version": settings.APP_VERSION,
        "database": "unknown",
        "redis": "unknown",
    }

    # ── Check PostgreSQL ──────────────────────────────────────────────────────
    try:
        await db.execute(text("SELECT 1"))
        status["database"] = "ok"
    except Exception as e:
        status["database"] = f"error: {str(e)}"

    # ── Check Redis ───────────────────────────────────────────────────────────
    try:
        r = aioredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
        await r.ping()
        await r.aclose()
        status["redis"] = "ok"
    except Exception as e:
        status["redis"] = f"error: {str(e)}"

    # ── Overall status ────────────────────────────────────────────────────────
    all_ok = all(v == "ok" for v in status.values() if isinstance(v, str))
    status["overall"] = "healthy" if all_ok else "degraded"

    return status


@router.get("/", tags=["Health"])
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }