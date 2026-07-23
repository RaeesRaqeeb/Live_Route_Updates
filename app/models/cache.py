# app/models/cache.py
from sqlalchemy import Column, String, Text, Integer, DateTime
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.base import TimestampMixin


class QueryCache(Base, TimestampMixin):
    """
    Stores cached API responses in PostgreSQL.
    Works alongside Redis cache as a persistent fallback.
    """
    __tablename__ = "query_cache"

    cache_key       = Column(String(255), unique=True, nullable=False, index=True)
    origin          = Column(String(100))
    destination     = Column(String(100))
    cached_response = Column(Text)          # JSON serialized response
    hit_count       = Column(Integer, default=0)
    expires_at      = Column(DateTime(timezone=True))