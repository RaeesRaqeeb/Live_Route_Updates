# app/models/user_query.py
from sqlalchemy import Column, String, Text, Integer, Float,Boolean
from app.models.base import TimestampMixin
from app.core.database import Base
from sqlalchemy import Column, String, Text, Float, Integer, Boolean, JSON, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from uuid import uuid4
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)

class UserQuery(Base, TimestampMixin):
    """
    Logs every user search for analytics and caching.
    """
    __tablename__ = "user_queries"

    id             = Column(String, primary_key=True, default=lambda: str(uuid4()))
    session_id     = Column(String, nullable=False)
    origin         = Column(String, nullable=True)
    destination    = Column(String, nullable=True)
    query_text     = Column(Text, nullable=True)
    query_type     = Column(String, nullable=True)
    response_time_ms = Column(Float, nullable=True)
    cache_hit      = Column(Boolean, default=False)
    sources_used   = Column(JSON, nullable=True)         # list of strings
    final_answer   = Column(Text, nullable=True)          # short summary
    full_result    = Column(JSONB, nullable=True)         # entire RouteInfoResponse as JSON
    alert_level    = Column(String, nullable=True)
    total_alerts   = Column(Integer, nullable=True, default=0)
    data_freshness_minutes = Column(Integer, nullable=True)
    token_count    = Column(Integer, nullable=True, default=0)
    alerts         = Column(JSONB, nullable=True)         # structured alert list
    weather_origin = Column(JSONB, nullable=True)
    weather_destination = Column(JSONB, nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
