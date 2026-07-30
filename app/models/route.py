# app/models/route.py
from sqlalchemy import Column, String, Float, Boolean, Text
from app.models.base import TimestampMixin
from app.core.database import Base
from sqlalchemy.orm import relationship


class Route(Base, TimestampMixin):
    """
    Stores known Pakistani routes between cities.
    Example: Lahore → Islamabad via M-2 Motorway
    """
    __tablename__ = "routes"

    origin_city       = Column(String(100), nullable=False, index=True)
    destination_city  = Column(String(100), nullable=False, index=True)
    route_name        = Column(String(200))          # e.g., "M-2 Motorway"
    distance_km       = Column(Float)
    estimated_hours   = Column(Float)
    route_type        = Column(String(50))           # motorway, highway, road
    is_active         = Column(Boolean, default=True)
    description       = Column(Text)
    scrape_results    = relationship("ScrapeResult", back_populates="route")
    corridor = Column(String(100))