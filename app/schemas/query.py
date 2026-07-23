# app/schemas/query.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum


class QueryType(str, Enum):
    ROUTE_NEWS    = "route_news"
    WEATHER       = "weather"
    ROAD_CONDITION = "road_condition"
    SAFETY        = "safety"
    ALL           = "all"


# ── Request Schema ────────────────────────────────────────────────────────────

class NaturalLanguageQuery(BaseModel):
    message: str
    query_type: str = "all"

class RouteQueryRequest(BaseModel):
    origin: str | None = None
    destination: str | None = None
    query_type: str = "all"
    message: str | None = None