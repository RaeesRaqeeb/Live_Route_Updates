# app/repositories/query_repo.py
import json
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from app.models.user_query import UserQuery
from app.utils.logger import get_logger

logger = get_logger(__name__)


class QueryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_query(
        self,
        session_id: str,
        origin: str,
        destination: str,
        response_time_ms: float,
        cache_hit: bool,
        sources_used: List[str],
        final_answer: str,
        token_count: int = 0,
    ) -> UserQuery:
        """Log a user query to the database for analytics."""
        query = UserQuery(
            session_id=session_id,
            origin_input=origin,
            destination_input=destination,
            normalized_origin=origin.strip().title(),
            normalized_dest=destination.strip().title(),
            response_time_ms=response_time_ms,
            cache_hit=cache_hit,
            sources_used=json.dumps(sources_used),
            final_answer=final_answer,
            token_count=token_count,
        )
        self.db.add(query)
        await self.db.flush()
        return query

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