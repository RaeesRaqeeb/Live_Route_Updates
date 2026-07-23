# app/routers/route_info.py
from __future__ import annotations

import time
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from app.services.route_discovery import get_or_create_route
from app.models.scrape_result import ScrapeResult
import hashlib
from app.core.database import AsyncSessionLocal  #  new session for background tasks
from app.core.dependencies import get_database   #  use this dependency
from app.schemas.query import RouteQueryRequest
from app.schemas.response import APIResponse, RouteInfoResponse
from app.services.cache_service import CacheService
from app.services.rag_service import RAGService
from app.services.scraper import ScraperService
# app/routers/route_info.py
from app.schemas.scrape import RawScrapeData          # ← from schemas, not services
from app.services.llm_extractor import LLMExtractor    # ← class is LLMExtractor, not LLMExtractorService
from app.services.weather_service import WeatherService
from app.repositories.query_repo import QueryRepository
from app.utils.logger import get_logger
from app.services.query_parser import QueryParserService
router = APIRouter()
import logging

# Initialize the logger for this module
logger = logging.getLogger(__name__)

FRESHNESS_WINDOW_HOURS = 3 

async def save_query_to_db(
    query: RouteQueryRequest,
    result: RouteInfoResponse,
    response_ms: float,
    cache_hit: bool,
):
    """
    Background task: logs query and final answer in DB.

    IMPORTANT:
    - Do NOT reuse the request-scoped db session here.
    - Create a new session using AsyncSessionLocal.
    """
    logger = get_logger(__name__)

    logger.info("Background task: save_query_to_db STARTED")

    async with AsyncSessionLocal() as session:
        try:
            repo = QueryRepository(session)
            await repo.log_query(
                session_id=str(uuid.uuid4()),
                origin=query.origin,
                destination=query.destination,
                response_time_ms=response_ms,
                cache_hit=cache_hit,
                sources_used=result.sources_scraped,
                final_answer=result.overall_summary,
                token_count=0,  # you can fill this later if you track tokens
            )
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Background task FAILED: {type(e).__name__}: {e}")
            # Don't crash the API response due to analytics logging
        finally:
            await session.close()


@router.post("/route/info", response_model=APIResponse)
async def get_route_information(
    query: RouteQueryRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_database),
    parser_service: QueryParserService = Depends(QueryParserService)
):
    # 1. Detect Natural Language Input
    if query.message:
        parsed_data = await parser_service.parse(query.message)
        
        # Handle the service's error fallback ("Unknown")
        if parsed_data.origin == "Unknown" or parsed_data.destination == "Unknown":
            raise HTTPException(
                status_code=400, 
                detail="Could not extract valid origin and destination from your message. Please try rephrasing or provide them explicitly."
            )
            
        origin = parsed_data.origin
        destination = parsed_data.destination
        # Optional: You can also leverage parsed_data.intents here if you want to override query.query_type

    # 2. Detect Structured Input
    elif query.origin and query.destination:
        origin = query.origin
        destination = query.destination

    # 3. Handle Invalid Requests
    else:
        raise HTTPException(
            status_code=400, 
            detail="You must provide either a natural language 'message' or explicit 'origin' and 'destination' fields."
        )
   
    start_time = time.time()
    cache_key = f"{origin}:{destination}:{query.query_type}"

    # # ── Step 1: Redis/memory cache (unchanged) ──
    cache_service = CacheService()
    # cached_result = await cache_service.get(cache_key)
    # if cached_result:
    #     cached_result["cache_hit"] = True
    #     return APIResponse.ok(cached_result, "Served from cache")

    # ── Step 2: Weather — still live, it's cheap and needs to be current ──
    weather_service = WeatherService()
    weather_origin = await weather_service.get_weather(origin)
    weather_dest = await weather_service.get_weather(destination)

    # ── Step 3: Get/register route, then query DB (NOT live scrape) ──
    route = await get_or_create_route(db, origin, destination)

    freshness_cutoff = datetime.now(timezone.utc) - timedelta(hours=FRESHNESS_WINDOW_HOURS)
    db_alerts_result = await db.execute(
        select(ScrapeResult).where(
            ScrapeResult.route_id == route.id,
            ScrapeResult.is_active == True,
            ScrapeResult.created_at >= freshness_cutoff,
        ).order_by(ScrapeResult.created_at.desc())
    )
    db_alerts = db_alerts_result.scalars().all()

    scraped_data = [
    {
        "source": a.source_name,
        "url": a.source_url,
        "content": a.summary or a.raw_content,
        "scrape_success": True,
        "error": None,
        "from_db": True,
        "headline": a.headline,
        "issue_type": a.issue_type,
        "severity": a.severity,
        "route_affected": a.route_affected,
        "summary": a.summary,
        "created_at": a.created_at,
    }
    for a in db_alerts
]

    data_age_minutes = 0
    if db_alerts:
        data_age_minutes = int((datetime.now(timezone.utc) - db_alerts[0].created_at).total_seconds() / 60)
    else:
        logger.info(f"No DB data for {origin}->{destination}, live scrape + extract + persist (first-time only)")
        scraper = ScraperService()
        extractor = LLMExtractor()
        raw_results = await scraper.scrape_route_news(origin, destination)

        scraped_data = []
        route_query = f"{origin} to {destination}"

        for raw in raw_results:
            if not raw.get("scrape_success") or not raw.get("content"):
                continue

            content = raw["content"]
            new_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

            raw_scrape = RawScrapeData(
                source=raw["source"],
                url=raw.get("url", ""),
                content=content,
            )

            extracted = await extractor.extract_route_info(raw_scrape, route_query)
            if extracted is None:  # None means extraction failed OR not route-related
                continue

            result_row = ScrapeResult(
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
            )
            db.add(result_row)

            scraped_data.append({
                "source": raw["source"],
                "url": raw.get("url", ""),
                "content": extracted.summary,
                "scrape_success": True,
                "error": None,
            })

        await db.commit() # ── Step 4: RAG / Answer (unchanged) ──

    logger.info(
    f"scraped_data prepared: {len(scraped_data)} items, "
    f"from_db={sum(1 for d in scraped_data if d.get('from_db'))}, "
    f"raw={sum(1 for d in scraped_data if not d.get('from_db'))}"
)
    rag = RAGService()
    answer = await rag.answer_route_query(
        query=f"{origin} to {destination}",
        scraped_docs=scraped_data,
        weather_origin=weather_origin,
        weather_destination=weather_dest,
    )

    response_ms = (time.time() - start_time) * 1000.0

    result = RouteInfoResponse(
        origin=origin,
        destination=destination,
        alert_level=answer.alert_level,
        overall_summary=answer.summary,
        weather_origin=weather_origin,
        weather_destination=weather_dest,
        alerts=answer.alerts,
        total_alerts_found=len(answer.alerts),
        sources_scraped=[d.get("source", "") for d in scraped_data],
        cache_hit=False,
        response_time_ms=round(response_ms, 2),
        data_freshness_minutes=data_age_minutes,
    )

    # Cache in Redis for a short window even for DB-served results —
    # avoids re-querying DB + re-running weather API for rapid repeat searches
    # await cache_service.set(cache_key, result.model_dump(), ttl=600)  # 10 min

    background_tasks.add_task(save_query_to_db, query, result, response_ms, False)

    return APIResponse.ok(result, "Route information fetched successfully")