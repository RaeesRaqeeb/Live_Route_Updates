# app/models/user_query.py
from sqlalchemy import Column, String, Text, Integer, Float,Boolean
from app.models.base import TimestampMixin
from app.core.database import Base


class UserQuery(Base, TimestampMixin):
    """
    Logs every user search for analytics and caching.
    """
    __tablename__ = "user_queries"

    session_id         = Column(String(100), index=True)
    origin_input       = Column(String(200))      # Raw user input: "Lahore"
    destination_input  = Column(String(200))      # Raw user input: "Islamabad"
    normalized_origin  = Column(String(100))      # After LLM normalization
    normalized_dest    = Column(String(100))
    response_time_ms   = Column(Float)            # How fast we answered
    cache_hit          = Column(Boolean, default=False)
    sources_used       = Column(Text)             # JSON list of sources used
    final_answer       = Column(Text)             # What we told the user
    token_count        = Column(Integer, default=0)