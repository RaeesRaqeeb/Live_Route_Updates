# app/api/route_info.py
"""
ASSUMPTIONS / THINGS TO VERIFY (read before relying on this):

1. RouteAlert (app.schemas.response) is a mutable Pydantic model -- I assign
   `alert.source = ...` directly on returned RouteAlert instances to strip an
   internal correlation tag before it reaches the user. If your RouteAlert is
   frozen/immutable this will raise; swap to `.copy(update=...)` (pydantic v1)
   or `.model_copy(update=...)` (pydantic v2) if so.

2. BatchExtractedItem's issue_type/severity are enums with a `.value` that is
   a lowercase string matching IssueType/Severity's own values ("accident",
   "high", etc) -- this is what rag_service.py already assumes, so I've kept
   that assumption. If Groq ever returns a value outside those enums,
   ScrapeResult construction below falls back to GENERAL/LOW rather than
   crashing.

3. I also had to patch app/services/rag_service.py -- it had a bug where
   `extractor.batch_extract()`'s (extracted, usage) tuple was unpacked as if
   it were the item list itself, which would crash the moment raw_docs was
   non-empty (exactly the path this endpoint now uses). Please review that
   diff too, not just this file.
"""

import hashlib
import time
from datetime import datetime, timedelta, timezone
from typing import List
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func

from app.core.dependencies import get_database
from app.models.route import Route
from app.models.scrape_result import ScrapeResult
from app.models.nhmp_closure import NHMPClosure
from app.models.user_query import UserQuery
from app.schemas.query import RouteQueryRequest
from app.schemas.response import APIResponse, RouteInfoResponse, RouteAlert, AlertLevel
from app.services.query_parser import QueryParserService
from app.services.weather_service import WeatherService
from app.services.cache_service import CacheService
from app.services.rag_service import RAGService
from app.utils.logger import get_logger
from app.services.corridor import get_corridor
from app.core.database import AsyncSessionLocal
logger = get_logger(__name__)
router = APIRouter()

FRESHNESS_WINDOW_HOURS = 3
NHMP_LOOKBACK_HOURS = 6
NHMP_ITEM_LIMIT = 10             # matches LLMExtractor.batch_extract's MAX_ITEMS_PER_BATCH
GB_ROUTES = ['Skardu', 'KKH', 'Northen areas', 'Hunza', 'Astore', 'Gilgit']
SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}

# Internal tag prefix used to correlate a RAG-returned alert back to the
# NHMPClosure it came from, so we can persist the *real* source name and
# original content -- see _build_nhmp_raw_items / _persist_nhmp_alerts.
_NHMP_TAG_PREFIX = "__nhmp__"

import json
from pydantic.json import pydantic_encoder # Built-in Pydantic encoder asset

# 1. Helper function to deep-serialize datetimes to JSON strings
def safe_json_serialize(data):
    if data is None:
        return None
    # This automatically serializes datetimes, UUIDs, and sets safely
    return json.loads(json.dumps(data, default=pydantic_encoder))


async def save_query_to_db(
        origin: str,
        destination: str,
        query_text: str,
        query_type: str | None,
        alert_level: str,
        final_answer: str,
        full_result: dict,
        alerts: list,
        total_alerts: int,
        sources_used: list[str],
        weather_origin,
        weather_destination,
        response_time_ms: float,
        token_count: int,
        data_freshness_minutes: int,
):
    """
    Background task: persist the full result into user_queries.
    Uses its own DB session — never reuses the request-scoped session.
    """
    logger = get_logger(__name__)
    logger.info("Background task: save_query_to_db STARTED")

    async with AsyncSessionLocal() as session:
        try:
            record = UserQuery(
                session_id=str(uuid.uuid4()),
                origin=origin,
                destination=destination,
                query_text=query_text,
                query_type=query_type,
                alert_level=alert_level,
                final_answer=final_answer,

                full_result=safe_json_serialize(full_result),
                alerts=safe_json_serialize(alerts),
                weather_origin=safe_json_serialize(weather_origin),
                weather_destination=safe_json_serialize(weather_destination),
                sources_used=safe_json_serialize(sources_used),

                response_time_ms=round(response_time_ms, 2),
                token_count=token_count,
                data_freshness_minutes=data_freshness_minutes,
                cache_hit=False,
            )
            session.add(record)
            await session.commit()
            logger.info(f"save_query_to_db: saved to user_queries for {origin}->{destination}")

        except Exception as e:
            await session.rollback()
            logger.error(f"save_query_to_db FAILED: {type(e).__name__}: {e}")
        finally:
            await session.close()
# ── Route lookup/creation ────────────────────────────────────────────────

async def get_or_create_route(session: AsyncSession, origin: str, destination: str) -> Route:
    origin_n, dest_n = origin.strip().title(), destination.strip().title()

    result = await session.execute(
        select(Route).where(
            Route.origin_city == origin_n,
            Route.destination_city == dest_n,
            Route.corridor == get_corridor(origin_n, dest_n),
            )
    )
    route = result.scalar_one_or_none()
    if route:
        return route

    route = Route(
        origin_city=origin_n,
        destination_city=dest_n,
        corridor=get_corridor(origin_n, dest_n),
        is_active=True,
    )
    session.add(route)
    await session.commit()
    await session.refresh(route)
    return route


# ── Branch A helpers: we already have scrape_result data -> no LLM at all ──

def _build_alerts_from_rows(rows: List[ScrapeResult]) -> List[RouteAlert]:
    return [
        RouteAlert(
            headline=r.headline,
            issue_type=r.issue_type.value if hasattr(r.issue_type, "value") else r.issue_type,
            severity=r.severity.value if hasattr(r.severity, "value") else r.severity,
            route_affected=r.route_affected,
            summary=r.summary,
            source=r.source_name,
            source_url=r.source_url or "",
            scraped_at=r.created_at,
        )
        for r in rows
    ]


def _alert_level_from_alerts(alerts: List[RouteAlert]) -> AlertLevel:
    if not alerts:
        return AlertLevel.UNKNOWN
    severities = [a.severity.lower() for a in alerts]
    if "high" in severities:
        return AlertLevel.DANGER
    if "medium" in severities:
        return AlertLevel.CAUTION
    if "low" in severities:
        return AlertLevel.SAFE
    return AlertLevel.UNKNOWN


def _deterministic_summary(
        origin: str,
        destination: str,
        alerts: List[RouteAlert],
        weather_origin,
        weather_dest,
        corridor_fallback: bool,
        age_minutes: int,
) -> str:
    """
    No-LLM summary for repeat queries against data we already have in
    scrape_results. Deliberately plain/templated rather than a narrative --
    the point of this branch is to avoid a Groq call entirely.
    """
    if not alerts:
        return (
            f"No active alerts on file for {origin} to {destination} "
            f"(last checked ~{age_minutes} min ago)."
        )

    top = max(alerts, key=lambda a: SEVERITY_RANK.get(a.severity.lower(), 0))
    parts = [
        f"{len(alerts)} alert(s) on file for {origin} to {destination} "
        f"(last checked ~{age_minutes} min ago)."
    ]
    if corridor_fallback:
        parts.append(
            "Note: these are corridor-level reports, not confirmed for your exact route segment."
        )
    parts.append(f"Most significant: [{top.severity.upper()}] {top.headline} — {top.summary}")
    if weather_origin:
        parts.append(f"Weather at {weather_origin.city}: {weather_origin.temperature_celsius}°C, {weather_origin.condition}.")
    if weather_dest:
        parts.append(f"Weather at {weather_dest.city}: {weather_dest.temperature_celsius}°C, {weather_dest.condition}.")
    return " ".join(parts)


# ── Branch B helpers: nothing fresh in scrape_results -> check nhmp_closures ──

def _content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


async def get_latest_nhmp_closures(
        db: AsyncSession, origin: str, destination: str, limit: int = NHMP_ITEM_LIMIT
) -> List[NHMPClosure]:
    origin_n, dest_n = origin.strip().title(), destination.strip().title()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=NHMP_LOOKBACK_HOURS)

    result = await db.execute(
        select(NHMPClosure)
        .where(
            NHMPClosure.created_at >= cutoff,
            or_(
                (NHMPClosure.origin == origin_n) & (NHMPClosure.destination == dest_n),
                (NHMPClosure.from_place.ilike(f"%{origin_n}%") & NHMPClosure.to_place.ilike(f"%{dest_n}%")),
                (NHMPClosure.route_label.ilike(f"%{origin_n}%") & NHMPClosure.route_label.ilike(f"%{dest_n}%")),
                ),
            )
        .order_by(NHMPClosure.reported_at.desc().nullslast(), NHMPClosure.created_at.desc())
        .limit(limit)
    )
    closures_list = list(result.scalars().all())

    # 2. Safely print your debug data using Python dictionary syntax or list comprehension
    # print("*" * 20)
    # print(" Data getting from NHMP closures :", [c.__dict__ for c in closures_list])
    # print("*" * 20)
    # exit()
    # 3. DO NOT use exit() here as it kills your entire running API server.
    return closures_list
    # return list(result.scalars().all())


def _nhmp_closure_content(closure: NHMPClosure) -> str:
    parts = []
    if closure.route_label:
        parts.append(f"Route: {closure.route_label}")
    if closure.alert_type:
        alert = closure.alert_type + (f" ({closure.sub_type})" if closure.sub_type else "")
        parts.append(f"Alert type: {alert}")
    if closure.lane_closure:
        parts.append(f"Lane closure status: {closure.lane_closure}")
    if closure.remarks:
        parts.append(f"Remarks: {closure.remarks}")
    return "\n".join(parts).strip()


def _build_nhmp_raw_items(closures: List[NHMPClosure]):
    """
    Build the dict shape RAGService/LLMExtractor expect (from_db absent ->
    treated as raw docs needing extraction), tagging `source` with a
    correlation id so we can map the eventual RouteAlert back to its
    NHMPClosure -- RAGService just forwards whatever we put in `source`
    straight into RouteAlert.source, and this string never enters the LLM
    prompt (only headline/summary/route_affected do), so it's safe to use
    internally and strip before the response goes out.
    """
    raw_items = []
    lookup = {}
    for c in closures:
        content = _nhmp_closure_content(c)
        tag = f"{_NHMP_TAG_PREFIX}{c.id}"
        lookup[tag] = {
            "content": content,
            "content_hash": c.content_hash or _content_hash(content),
            "display_source": c.source or "NHMP_API",
        }
        timestamp = c.reported_at or c.created_at
        raw_items.append({
            "source": tag,
            "url": None,
            "content": content,
            "scrape_success": bool(content),
            "post_created_at": timestamp.isoformat() if timestamp else "Unknown time",
        })
    return raw_items, lookup


async def _persist_nhmp_alerts(
        db: AsyncSession, route: Route, alerts: List[RouteAlert], closure_lookup: dict
) -> List[ScrapeResult]:
    """Write RAG-extracted NHMP alerts into scrape_results so the next query for
    this route hits Branch A (no LLM) instead of re-checking NHMP+LLM again."""
    stored: List[ScrapeResult] = []

    for alert in alerts:
        info = closure_lookup.get(alert.source)
        if info is None:
            logger.warning(f"Could not correlate alert '{alert.headline}' back to an NHMPClosure; skipping storage")
            continue

        c_hash = info["content_hash"]
        existing = (await db.execute(
            select(ScrapeResult).where(
                ScrapeResult.route_id == route.id,
                ScrapeResult.content_hash == c_hash,
                )
        )).scalar_one_or_none()
        if existing:
            stored.append(existing)
            continue

        try:
            issue_type_enum = IssueType(alert.issue_type)
        except ValueError:
            issue_type_enum = IssueType.GENERAL
        try:
            severity_enum = Severity(alert.severity)
        except ValueError:
            severity_enum = Severity.LOW

        row = ScrapeResult(
            route_id=route.id,
            source_name=info["display_source"],
            source_url=alert.source_url or None,
            headline=alert.headline,
            route_affected=alert.route_affected,
            issue_type=issue_type_enum,
            severity=severity_enum,
            raw_content=info["content"],
            summary=alert.summary,
            is_active=True,
            content_hash=c_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=45),  # matches scheduler cadence
        )
        db.add(row)
        stored.append(row)

    if stored:
        await db.commit()
        for row in stored:
            await db.refresh(row)

    return stored


def _clean_alert_sources(alerts: List[RouteAlert], closure_lookup: dict) -> None:
    """Replace internal correlation tags with the real source name in-place."""
    for alert in alerts:
        info = closure_lookup.get(alert.source)
        if info:
            alert.source = info["display_source"]


# ── Endpoint ──────────────────────────────────────────────────────────────
#
# @router.post("/route/info", response_model=APIResponse)
# async def get_route_information(
#         query: RouteQueryRequest,
#         background_tasks: BackgroundTasks,
#         db: AsyncSession = Depends(get_database),
#         parser_service: QueryParserService = Depends(QueryParserService),
# ):
#     # 1. Natural-language input
#     if query.message:
#         parsed_data = await parser_service.parse(query.message)
#         if parsed_data.origin == "Unknown" or parsed_data.destination == "Unknown":
#             raise HTTPException(
#                 status_code=400,
#                 detail="Could not extract valid origin and destination from your message. Please try rephrasing or provide them explicitly.",
#             )
#         origin = parsed_data.origin
#         destination = parsed_data.destination
#
#     # 2. Structured input
#     elif query.origin and query.destination:
#         origin = query.origin
#         destination = query.destination
#
#     # 3. Invalid
#     else:
#         raise HTTPException(
#             status_code=400,
#             detail="You must provide either a natural language 'message' or explicit 'origin' and 'destination' fields.",
#         )
#
#     start_time = time.time()
#     cache_key = f"{origin}:{destination}:{query.query_type}"
#     cache_service = CacheService()
#
#     weather_service = WeatherService()
#     weather_origin = await weather_service.get_weather(origin)
#     weather_dest = await weather_service.get_weather(destination)
#
#     total_token = 0
#     data_age_minutes = 0
#
#     # ── Step 1: check user_queries for a fresh result ──
#     freshness_cutoff = datetime.now(timezone.utc) - timedelta(hours=FRESHNESS_WINDOW_HOURS)
#
#     cached_row = await db.execute(
#         select(UserQuery)
#         .where(
#             func.lower(UserQuery.origin) == origin.lower(),
#             func.lower(UserQuery.destination) == destination.lower(),
#             UserQuery.created_at >= freshness_cutoff,
#             )
#         .order_by(UserQuery.created_at.desc())
#         .limit(1)
#     )
#     cached_query = cached_row.scalars().first()
#
#     if cached_query:
#         # ── Branch A: fresh row found in user_queries — return directly ──
#         logger.info(f"user_queries cache hit for {origin}->{destination}")
#
#         data_age_minutes = int(
#             (datetime.now(timezone.utc) - cached_query.created_at).total_seconds() / 60
#         )
#
#         result = RouteInfoResponse(
#             origin=origin,
#             destination=destination,
#             alert_level=cached_query.alert_level or "unknown",
#             overall_summary=cached_query.final_answer or "",
#             weather_origin=cached_query.weather_origin,
#             weather_destination=cached_query.weather_destination,
#             alerts=cached_query.alerts or [],
#             total_alerts_found=cached_query.total_alerts or 0,
#             sources_scraped=cached_query.sources_used or [],
#             cache_hit=True,
#             response_time_ms=round((time.time() - start_time) * 1000.0, 2),
#             data_freshness_minutes=data_age_minutes,
#             total_token=0,
#         )
#
#         return APIResponse.ok(result, "Route information fetched from recent query cache.")
#
#     # ── Step 2: no fresh user_queries row → fetch fresh data ──
#     logger.info(f"No fresh user_queries for {origin}->{destination}; fetching fresh data")
#
#     route = await get_or_create_route(db, origin, destination)
#
#     # ── Step 2a: check scrape_results ──
#     db_alerts_result = await db.execute(
#         select(ScrapeResult).where(
#             ScrapeResult.route_id == route.id,
#             ScrapeResult.is_active == True,
#             ScrapeResult.created_at >= freshness_cutoff,
#             ).order_by(ScrapeResult.created_at.desc())
#     )
#     db_alerts = db_alerts_result.scalars().all()
#     is_corridor_fallback = False
#
#     if not db_alerts and route.corridor:
#         corridor_result = await db.execute(
#             select(ScrapeResult)
#             .join(Route, Route.id == ScrapeResult.route_id)
#             .where(
#                 Route.corridor == route.corridor,
#                 ScrapeResult.is_active == True,
#                 ScrapeResult.created_at >= freshness_cutoff,
#                 )
#             .order_by(ScrapeResult.created_at.desc())
#         )
#         db_alerts = corridor_result.scalars().all()
#         is_corridor_fallback = bool(db_alerts)
#
#     if db_alerts:
#         # ── Branch B: fresh scrape_results ──
#         alerts = _build_alerts_from_rows(db_alerts)
#         alert_level = _alert_level_from_alerts(alerts)
#         data_age_minutes = int(
#             (datetime.now(timezone.utc) - db_alerts[0].created_at).total_seconds() / 60
#         )
#         overall_summary = _deterministic_summary(
#             origin, destination, alerts, weather_origin, weather_dest,
#             is_corridor_fallback, data_age_minutes,
#         )
#
#     else:
#         # ── Step 2b: check nhmp_closures ──
#         logger.info(f"No fresh scrape_results for {origin}->{destination}; checking nhmp_closures")
#         closures = await get_latest_nhmp_closures(db, origin, destination)
#
#         if not closures:
#             # ── Branch C: no data anywhere ──
#             logger.warning(f"No scrape_results AND no nhmp_closures for {origin}->{destination}")
#             rag = RAGService()
#             answer = await rag.answer_route_query(
#                 query=f"{origin} to {destination}",
#                 scraped_docs=[],
#                 weather_origin=weather_origin,
#                 weather_destination=weather_dest,
#                 data_fetch_failed=True,
#             )
#             alerts = answer.alerts
#             alert_level = answer.alert_level
#             overall_summary = answer.summary
#             total_token += answer.total_tokens
#
#         else:
#             # ── Branch D: NHMP fallback ──
#             raw_items, closure_lookup = _build_nhmp_raw_items(closures)
#             rag = RAGService()
#             answer = await rag.answer_route_query(
#                 query=f"{origin} to {destination}",
#                 scraped_docs=raw_items,
#                 weather_origin=weather_origin,
#                 weather_destination=weather_dest,
#                 data_fetch_failed=False,
#             )
#             total_token += answer.total_tokens
#
#             if answer.alerts:
#                 await _persist_nhmp_alerts(db, route, answer.alerts, closure_lookup)
#                 _clean_alert_sources(answer.alerts, closure_lookup)
#                 logger.info(
#                     f"NHMP fallback: stored {len(answer.alerts)} alert(s) for "
#                     f"{origin}->{destination} ({total_token} tokens)"
#                 )
#             else:
#                 logger.info(
#                     f"NHMP closures present but RAG found nothing for {origin}->{destination}"
#                 )
#
#             alerts = answer.alerts
#             alert_level = answer.alert_level
#             overall_summary = answer.summary
#
#     response_ms = (time.time() - start_time) * 1000.0
#     logger.info(f"Token count: {total_token}")
#
#     result = RouteInfoResponse(
#         origin=origin,
#         destination=destination,
#         alert_level=alert_level,
#         overall_summary=overall_summary,
#         weather_origin=weather_origin,
#         weather_destination=weather_dest,
#         alerts=alerts,
#         total_alerts_found=len(alerts),
#         sources_scraped=[a.source for a in alerts],
#         cache_hit=False,
#         response_time_ms=round(response_ms, 2),
#         data_freshness_minutes=data_age_minutes,
#         total_token=total_token,
#     )
#
#     await cache_service.set(cache_key, result.model_dump(), ttl=600)
#
#     background_tasks.add_task(
#         save_query_to_db,
#         origin=origin,
#         destination=destination,
#         query_text=query.message or f"{origin} to {destination}",
#         query_type=query.query_type,
#         alert_level=alert_level,
#         final_answer=overall_summary,
#         full_result=result.model_dump(),
#         alerts=[a.model_dump() if hasattr(a, "model_dump") else a for a in alerts],
#         total_alerts=len(alerts),
#         sources_used=[a.source for a in alerts],
#         weather_origin=weather_origin,
#         weather_destination=weather_dest,
#         response_time_ms=response_ms,
#         token_count=total_token,
#         data_freshness_minutes=data_age_minutes,
#     )
#
#     return APIResponse.ok(result, "Route information fetched successfully")


# ── GB/KKH corridor keywords — if user query matches any of these,
#    pull all own_fb_page posts (they cover the whole GB region) ──
GB_CORRIDOR_KEYWORDS = {
    "skardu", "gilgit", "hunza", "kkh", "karakoram", "karakorum",
    "astore", "gb", "chilas", "naran", "babusar", "jaglot", "jsr",
    "n-35", "n35", "s-1", "n-15", "n15", "ghanche", "ghizer",
    "diamer", "kohistan", "besham", "thakot", "batgram",
}

def _is_gb_query(origin: str, destination: str) -> bool:
    """Return True if the user's origin or destination touches the GB/KKH corridor."""
    combined = f"{origin} {destination}".lower()
    return any(kw in combined for kw in GB_CORRIDOR_KEYWORDS)


@router.post("/route/info", response_model=APIResponse)
async def get_route_information(
        query: RouteQueryRequest,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_database),
        parser_service: QueryParserService = Depends(QueryParserService),
):
    # 1. Natural-language input
    if query.message:
        parsed_data = await parser_service.parse(query.message)
        if parsed_data.origin == "Unknown" or parsed_data.destination == "Unknown":
            raise HTTPException(
                status_code=400,
                detail="Could not extract valid origin and destination from your message. Please try rephrasing or provide them explicitly.",
            )
        origin = parsed_data.origin
        destination = parsed_data.destination

    # 2. Structured input
    elif query.origin and query.destination:
        origin = query.origin
        destination = query.destination

    # 3. Invalid
    else:
        raise HTTPException(
            status_code=400,
            detail="You must provide either a natural language 'message' or explicit 'origin' and 'destination' fields.",
        )

    start_time = time.time()
    cache_key = f"{origin}:{destination}:{query.query_type}"
    cache_service = CacheService()

    weather_service = WeatherService()
    weather_origin = await weather_service.get_weather(origin)
    weather_dest = await weather_service.get_weather(destination)

    total_token = 0
    data_age_minutes = 0

    # ══════════════════════════════════════════════════════════
    # Step 1: user_queries cache
    # ══════════════════════════════════════════════════════════
    freshness_cutoff = datetime.now(timezone.utc) - timedelta(hours=FRESHNESS_WINDOW_HOURS)

    cached_row = await db.execute(
        select(UserQuery)
        .where(
            func.lower(UserQuery.origin) == origin.lower(),
            func.lower(UserQuery.destination) == destination.lower(),
            UserQuery.created_at >= freshness_cutoff,
            )
        .order_by(UserQuery.created_at.desc())
        .limit(1)
    )
    cached_query = cached_row.scalars().first()

    if cached_query:
        logger.info(f"user_queries cache hit for {origin}->{destination}")
        data_age_minutes = int(
            (datetime.now(timezone.utc) - cached_query.created_at).total_seconds() / 60
        )
        result = RouteInfoResponse(
            origin=origin,
            destination=destination,
            alert_level=cached_query.alert_level or "unknown",
            overall_summary=cached_query.final_answer or "",
            weather_origin=cached_query.weather_origin,
            weather_destination=cached_query.weather_destination,
            alerts=cached_query.alerts or [],
            total_alerts_found=cached_query.total_alerts or 0,
            sources_scraped=cached_query.sources_used or [],
            cache_hit=True,
            response_time_ms=round((time.time() - start_time) * 1000.0, 2),
            data_freshness_minutes=data_age_minutes,
            total_token=0,
        )
        return APIResponse.ok(result, "Route information fetched from recent query cache.")

    # ══════════════════════════════════════════════════════════
    # Step 2: scrape_results lookup
    # ══════════════════════════════════════════════════════════
    logger.info(f"No fresh user_queries for {origin}->{destination}; checking scrape_results")

    route = await get_or_create_route(db, origin, destination)
    db_alerts = []
    is_corridor_fallback = False

    # ── 2a: exact route_id match ──
    db_alerts_result = await db.execute(
        select(ScrapeResult)
        .where(
            ScrapeResult.route_id == route.id,
            ScrapeResult.is_active == True,
            ScrapeResult.created_at >= freshness_cutoff,
            )
        .order_by(ScrapeResult.created_at.desc())
    )
    db_alerts = db_alerts_result.scalars().all()

    # ── 2b: corridor fallback ──
    if not db_alerts and route.corridor:
        logger.info(f"No direct match; trying corridor '{route.corridor}' for {origin}->{destination}")
        corridor_result = await db.execute(
            select(ScrapeResult)
            .join(Route, Route.id == ScrapeResult.route_id)
            .where(
                Route.corridor == route.corridor,
                ScrapeResult.is_active == True,
                ScrapeResult.created_at >= freshness_cutoff,
                )
            .order_by(ScrapeResult.created_at.desc())
        )
        db_alerts = corridor_result.scalars().all()
        is_corridor_fallback = bool(db_alerts)

    # ── 2c: origin/destination column match (NHMP rows have these) ──
    if not db_alerts:
        logger.info(f"No corridor match; trying origin/destination columns for {origin}->{destination}")
        od_result = await db.execute(
            select(ScrapeResult)
            .where(
                func.lower(ScrapeResult.origin) == origin.lower(),
                func.lower(ScrapeResult.destination) == destination.lower(),
                ScrapeResult.is_active == True,
                ScrapeResult.created_at >= freshness_cutoff,
                )
            .order_by(ScrapeResult.created_at.desc())
        )
        db_alerts = od_result.scalars().all()

    # ── 2d: GB/KKH corridor — pull ALL own_fb_page posts ──
    # Facebook posts cover the whole GB region without explicit origin/dest.
    # If the user's query mentions any GB keyword, include them regardless.
    fb_alerts = []
    if _is_gb_query(origin, destination):
        logger.info(f"GB/KKH query detected for '{origin}->{destination}'; fetching own_fb_page rows")
        fb_result = await db.execute(
            select(ScrapeResult)
            .where(
                ScrapeResult.source_name == "own_fb_page",
                ScrapeResult.is_active == True,
                ScrapeResult.created_at >= freshness_cutoff,
                )
            .order_by(ScrapeResult.created_at.desc())
        )
        fb_alerts = fb_result.scalars().all()
        if fb_alerts:
            logger.info(f"Found {len(fb_alerts)} own_fb_page row(s) for GB/KKH query")

    # ── Merge: structured alerts + FB posts (deduplicated by id) ──
    if fb_alerts:
        existing_ids = {r.id for r in db_alerts}
        extra_fb = [r for r in fb_alerts if r.id not in existing_ids]
        db_alerts = list(db_alerts) + extra_fb
        logger.info(f"Total after merging FB posts: {len(db_alerts)} row(s)")

    # ══════════════════════════════════════════════════════════
    # Step 3: build response
    # ══════════════════════════════════════════════════════════

    if db_alerts:
        logger.info(
            f"Passing {len(db_alerts)} row(s) to RAGService for {origin}->{destination} "
            f"({'corridor fallback' if is_corridor_fallback else 'direct + FB'})"
        )

        scraped_docs = _rows_to_scraped_docs(db_alerts)

        rag = RAGService()
        answer = await rag.answer_route_query(
            query=f"{origin} to {destination}",
            scraped_docs=scraped_docs,
            weather_origin=weather_origin,
            weather_destination=weather_dest,
            data_fetch_failed=False,
        )
        total_token += answer.total_tokens
        alerts = answer.alerts
        alert_level = answer.alert_level
        overall_summary = answer.summary
        data_age_minutes = int(
            (datetime.now(timezone.utc) - db_alerts[0].created_at).total_seconds() / 60
        )

    else:
        logger.warning(f"No scrape_results at all for {origin}->{destination}")
        rag = RAGService()
        answer = await rag.answer_route_query(
            query=f"{origin} to {destination}",
            scraped_docs=[],
            weather_origin=weather_origin,
            weather_destination=weather_dest,
            data_fetch_failed=True,
        )
        total_token += answer.total_tokens
        alerts = answer.alerts
        alert_level = answer.alert_level
        overall_summary = answer.summary

    response_ms = (time.time() - start_time) * 1000.0
    logger.info(f"Token count: {total_token}")

    result = RouteInfoResponse(
        origin=origin,
        destination=destination,
        alert_level=alert_level,
        overall_summary=overall_summary,
        weather_origin=weather_origin,
        weather_destination=weather_dest,
        alerts=alerts,
        total_alerts_found=len(alerts),
        sources_scraped=[a.source for a in alerts],
        cache_hit=False,
        response_time_ms=round(response_ms, 2),
        data_freshness_minutes=data_age_minutes,
        total_token=total_token,
    )

    await cache_service.set(cache_key, result.model_dump(), ttl=600)

    background_tasks.add_task(
        save_query_to_db,
        origin=origin,
        destination=destination,
        query_text=query.message or f"{origin} to {destination}",
        query_type=query.query_type,
        alert_level=alert_level,
        final_answer=overall_summary,
        full_result=result.model_dump(),
        alerts=[a.model_dump() if hasattr(a, "model_dump") else a for a in alerts],
        total_alerts=len(alerts),
        sources_used=[a.source for a in alerts],
        weather_origin=weather_origin,
        weather_destination=weather_dest,
        response_time_ms=response_ms,
        token_count=total_token,
        data_freshness_minutes=data_age_minutes,
    )

    return APIResponse.ok(result, "Route information fetched successfully")

# ══════════════════════════════════════════════════════════════
# Helper: convert ScrapeResult ORM rows → scraped_docs dicts
# This replaces _build_alerts_from_rows + _build_nhmp_raw_items
# ══════════════════════════════════════════════════════════════

def _rows_to_scraped_docs(rows: list[ScrapeResult]) -> list[dict]:
    """
    Convert ScrapeResult ORM rows into the dict format RAGService expects.
    Works for ALL source types (NHMP, Facebook, SERPAPI, etc.) since the
    scheduler now normalises everything into the same ScrapeResult columns.
    """
    docs = []
    for row in rows:
        docs.append({
            # identity
            "source": row.source_name,
            "url": row.source_url or "",
            # pre-structured fields (scheduler already extracted these)
            "headline": row.headline or "",
            "route_affected": row.route_affected or "",
            "origin": row.origin or "",
            "destination": row.destination or "",
            "issue_type": row.issue_type or "",
            "severity": row.severity or "medium",
            "summary": row.summary or "",
            # raw text fallback (RAG can re-read if needed)
            "content": row.summary or row.raw_content or "",
            "scrape_success": True,
            "from_db": True,   # tells RAGService: skip re-extraction
            "created_at": row.created_at.isoformat() if row.created_at else "",
        })
    return docs


from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

# Assuming this is inside your router setup
@router.get("/routes")
async def get_routes(
        db: AsyncSession = Depends(get_database),
):
    # 1. Execute the query
    result = await db.execute(select(ScrapeResult))

    # 2. Extract the objects from the result mapping
    routes = result.scalars().all()

    # Debug print statement safely executed
    print("Data:", routes)

    # 3. Return the list (FastAPI automatically serializes this)
    return routes
