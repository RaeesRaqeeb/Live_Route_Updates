# app/models/nhmp_closure.py
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.models.base import Base

class NHMPClosure(Base):
    __tablename__ = "nhmp_closures"

    id = Column(Integer, primary_key=True)
    origin = Column(String, nullable=False, index=True)
    destination = Column(String, nullable=False, index=True)
    source = Column(String, nullable=False)        # "NHMP_API" or "NHMP_PAGE"
    alert_type = Column(String, nullable=True)
    sub_type = Column(String, nullable=True)
    route_label = Column(String, nullable=True)     # raw "Lahore to Islamabad" from NHMP
    from_place = Column(String, nullable=True)
    to_place = Column(String, nullable=True)
    remarks = Column(Text, nullable=True)
    lane_closure = Column(String, nullable=True)
    reported_at = Column(DateTime(timezone=True), nullable=True)  # NHMP's own timestamp
    content_hash = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())