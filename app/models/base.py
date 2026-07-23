# app/models/base.py
from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.sql import func
from app.core.database import Base


class TimestampMixin:
    """Adds created_at and updated_at to every model."""
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())