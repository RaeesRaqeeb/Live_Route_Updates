# app/models/scrape_result.py
from sqlalchemy import Column, String, Text, Integer, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.models.base import TimestampMixin
from app.core.database import Base


class ScrapeResult(Base, TimestampMixin):
    """
    Unified store for ALL scraped sources (NHMP, Facebook, SERPAPI, etc.).
    route_id is nullable — resolved lazily at query time via origin/destination
    columns when the scheduler doesn't know the route upfront.
    """
    __tablename__ = "scrape_results"

    # ── Route linkage (nullable — not required at scrape time) ──
    route_id         = Column(
        Integer,
        ForeignKey("routes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Source identity ──
    source_name      = Column(String(100), nullable=False)
    source_url       = Column(String(500), nullable=True)

    # ── Extracted / structured fields ──
    headline         = Column(String(500), nullable=True)
    route_affected   = Column(String(200), nullable=True)
    origin           = Column(String(200), nullable=True)
    destination      = Column(String(200), nullable=True)

    # Plain strings — avoids PostgreSQL enum uppercase/lowercase mismatch
    # Valid values: accident, blockage, weather, construction, incident, security, general
    issue_type       = Column(String(50),  nullable=True, default="general")
    # Valid values: low, medium, high
    severity         = Column(String(20),  nullable=True, default="medium")

    raw_content      = Column(Text, nullable=True)
    summary          = Column(Text, nullable=True)

    # ── Deduplication & lifecycle ──
    content_hash     = Column(String(64), index=True, nullable=True)
    is_active        = Column(Boolean, default=True, nullable=False)
    expires_at       = Column(DateTime(timezone=True), nullable=True)

    # ── Relationship ──
    route            = relationship("Route", back_populates="scrape_results")