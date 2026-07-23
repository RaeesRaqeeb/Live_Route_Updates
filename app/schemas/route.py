# app/schemas/route.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class RouteCreate(BaseModel):
    """Schema for creating a new route in the database."""
    origin_city: str = Field(..., min_length=2, max_length=100)
    destination_city: str = Field(..., min_length=2, max_length=100)
    route_name: Optional[str] = None
    distance_km: Optional[float] = Field(None, gt=0)
    estimated_hours: Optional[float] = Field(None, gt=0)
    route_type: Optional[str] = None   # motorway, highway, road
    description: Optional[str] = None


class RouteUpdate(BaseModel):
    """Schema for updating an existing route."""
    route_name: Optional[str] = None
    distance_km: Optional[float] = None
    estimated_hours: Optional[float] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


class RouteSchema(RouteCreate):
    """Full route schema with DB fields."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True