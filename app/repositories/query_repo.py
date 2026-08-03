# app/repositories/query_repo.py
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from app.models.user_query import UserQuery
from app.utils.logger import get_logger

logger = get_logger(__name__)


from sqlalchemy import Column, String, Text, Float, Integer, Boolean, JSON, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from uuid import uuid4

# Make sure your UserQuery model has these columns:
#
#   id             = Column(String, primary_key=True, default=lambda: str(uuid4()))
#   session_id     = Column(String, nullable=False)
#   origin         = Column(String, nullable=True)
#   destination    = Column(String, nullable=True)
#   query_text     = Column(Text, nullable=True)
#   query_type     = Column(String, nullable=True)
#   response_time_ms = Column(Float, nullable=True)
#   cache_hit      = Column(Boolean, default=False)
#   sources_used   = Column(JSON, nullable=True)         # list of strings
#   final_answer   = Column(Text, nullable=True)          # short summary
#   full_result    = Column(JSONB, nullable=True)         # entire RouteInfoResponse as JSON
#   alert_level    = Column(String, nullable=True)
#   total_alerts   = Column(Integer, nullable=True, default=0)
#   data_freshness_minutes = Column(Integer, nullable=True)
#   token_count    = Column(Integer, nullable=True, default=0)
#   alerts         = Column(JSONB, nullable=True)         # structured alert list
#   weather_origin = Column(JSONB, nullable=True)
#   weather_destination = Column(JSONB, nullable=True)
#   created_at     = Column(DateTime(timezone=True), server_default=func.now())


class QueryRepository:
    def __init__(self, session):
        self.session = session

    async def log_query(
            self,
            session_id: str,
            origin: str | None,
            destination: str | None,
            query_text: str | None = None,
            query_type: str = "route_info",
            response_time_ms: float = 0.0,
            cache_hit: bool = False,
            sources_used: list[str] | None = None,
            final_answer: str | None = None,
            full_result: str | dict | None = None,       # accepts JSON string or dict
            alert_level: str | None = None,
            total_alerts: int = 0,
            data_freshness_minutes: int | None = None,
            token_count: int = 0,
            alerts: list[dict] | None = None,
            weather_origin: dict | None = None,
            weather_destination: dict | None = None,
    ):
        import json as json_lib

        # If full_result came as a JSON string, parse it so JSONB stores it as object
        if isinstance(full_result, str):
            try:
                full_result = json_lib.loads(full_result)
            except (json_lib.JSONDecodeError, TypeError):
                pass  # store as-is

        record = UserQuery(
            id=str(uuid4()),
            session_id=session_id,
            origin=origin,
            destination=destination,
            query_text=query_text,
            query_type=query_type,
            response_time_ms=response_time_ms,
            cache_hit=cache_hit,
            sources_used=sources_used or [],
            final_answer=final_answer,
            full_result=full_result,
            alert_level=str(alert_level) if alert_level else None,
            total_alerts=total_alerts,
            data_freshness_minutes=data_freshness_minutes,
            token_count=token_count,
            alerts=alerts or [],
            weather_origin=weather_origin,
            weather_destination=weather_destination,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_popular_routes(self, limit: int = 10) -> List[dict]:
        """Get most searched routes for pre-warming cache."""
        stmt = (
            select(
                UserQuery.normalized_origin,
                UserQuery.normalized_dest,
                func.count(UserQuery.id).label("search_count"),
            )
            .group_by(UserQuery.normalized_origin, UserQuery.normalized_dest)
            .order_by(desc("search_count"))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [
            {"origin": row[0], "destination": row[1], "count": row[2]}
            for row in result.fetchall()
        ]

    async def get_avg_response_time(self) -> float:
        """Analytics: average API response time."""
        stmt = select(func.avg(UserQuery.response_time_ms))
        result = await self.db.execute(stmt)
        return round(result.scalar() or 0.0, 2)