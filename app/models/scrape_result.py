# app/models/scrape_result.py
from sqlalchemy import Column, String, Text, Enum, Integer, ForeignKey, Boolean,DateTime
from sqlalchemy.orm import relationship
import enum
from app.models.base import TimestampMixin
from app.core.database import Base



class IssueType(str, enum.Enum):
    ACCIDENT     = "accident"
    BLOCKAGE     = "blockage"
    WEATHER      = "weather"
    CONSTRUCTION = "construction"
    SECURITY     = "security"
    GENERAL      = "general"


class Severity(str, enum.Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


class ScrapeResult(Base, TimestampMixin):
    """
    Stores extracted information from Pakistani news sites and NHMP.
    Each row is one news item/alert about a specific route.
    """
    __tablename__ = "scrape_results"

    route_id         = Column(Integer, ForeignKey("routes.id"), nullable=True)
    source_name      = Column(String(100))            # dawn, geo, nhmp, etc.
    source_url       = Column(String(500))
    headline         = Column(String(500))
    route_affected   = Column(String(200))            # e.g., "M-2 near Lahore"
    issue_type       = Column(Enum(IssueType), default=IssueType.GENERAL)
    severity         = Column(Enum(Severity), default=Severity.LOW)
    raw_content      = Column(Text)                   # Original scraped text
    summary          = Column(Text)                   # LLM-generated summary
    is_active        = Column(Boolean, default=True)
    # In ScrapeResult model, add:
    content_hash = Column(String(64), index=True)  # SHA256 of raw_content, skip LLM if unchanged
    expires_at = Column(DateTime(timezone=True))    # when this alert should be considered stale
    route = relationship("Route", back_populates="scrape_results")