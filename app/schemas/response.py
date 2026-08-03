# app/schemas/response.py
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


class AlertLevel(str, Enum):
    SAFE     = "safe"
    CAUTION  = "caution"
    DANGER   = "danger"
    UNKNOWN  = "unknown"


# ── Weather Response ──────────────────────────────────────────────────────────
class WeatherInfo(BaseModel):
    city: str
    temperature_celsius: float
    feels_like: float
    condition: str                         # e.g., "Partly Cloudy"
    humidity_percent: int
    wind_speed_kmh: float
    visibility_km: float
    is_travel_friendly: bool
    advisory: Optional[str] = None


# ── Single News/Alert Item ────────────────────────────────────────────────────
class RouteAlert(BaseModel):
    headline: str
    issue_type: str                        # accident, blockage, weather, etc.
    severity: str                          # low, medium, high
    route_affected: Optional[str] = None
    summary: str
    source: str                            # dawn, geo, nhmp, etc.
    source_url: Optional[str]= None
    scraped_at: datetime
    is_verified: bool = False


# ── Full Route Information Response ──────────────────────────────────────────
class RouteInfoResponse(BaseModel):
    origin: str
    destination: str
    alert_level: AlertLevel
    overall_summary: str                   # LLM-generated paragraph

    weather_origin: Optional[WeatherInfo] = None
    weather_destination: Optional[WeatherInfo] = None
    alerts: List[RouteAlert] = []

    total_alerts_found: int = 0
    sources_scraped: List[str] = []
    cache_hit: bool = False
    data_freshness_minutes: int = 0        # How old is the data?
    response_time_ms: float = 0.0
    total_token: int =0
    # in RouteInfoResponse schema, add:
    data_received_at: Optional[datetime] = None
    next_update_expected_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "origin": "Lahore",
                "destination": "Islamabad",
                "alert_level": "caution",
                "overall_summary": "Route is generally clear. Minor fog reported near Gujranwala...",
                "alerts": [],
                "total_alerts_found": 2,
                "cache_hit": True,
            }
        }


# ── Generic API Wrapper ───────────────────────────────────────────────────────
class APIResponse(BaseModel):
    success: bool = True
    message: str = "OK"
    data: Optional[Any] = None
    error: Optional[str] = None

    @classmethod
    def ok(cls, data: Any, message: str = "Success") -> "APIResponse":
        return cls(success=True, message=message, data=data)

    @classmethod
    def fail(cls, error: str) -> "APIResponse":
        return cls(success=False, error=error)