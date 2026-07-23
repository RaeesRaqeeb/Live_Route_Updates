# app/services/weather_service.py
import httpx
from typing import Optional
from app.core.config import settings
from app.schemas.response import WeatherInfo
from app.schemas.weather import WeatherAPIResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)

OPENWEATHER_BASE = "https://api.openweathermap.org/data/2.5/weather"


class WeatherService:
    def __init__(self):
        self.api_key = settings.OPENWEATHER_API_KEY
        self.timeout = httpx.Timeout(10.0)

    async def get_weather(self, city: str) -> Optional[WeatherInfo]:
        """
        Fetch current weather for a Pakistani city.
        Returns a clean WeatherInfo schema.
        """
        try:
            params = {
                "q": f"{city},PK",
                "appid": self.api_key,
                "units": "metric",
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(OPENWEATHER_BASE, params=params)
                response.raise_for_status()

            data = response.json()
            raw = WeatherAPIResponse(**data)

            # ── Convert to our clean schema ───────────────────────────────────
            visibility_km = round((raw.visibility or 10000) / 1000, 1)
            wind_kmh = round(raw.wind.speed * 3.6, 1)   # m/s → km/h
            condition = raw.weather[0].description.title() if raw.weather else "Unknown"

            is_friendly = (
                raw.main.temp < 40
                and raw.main.humidity < 90
                and visibility_km > 1.0
                and wind_kmh < 60
            )

            return WeatherInfo(
                city=raw.name,
                temperature_celsius=round(raw.main.temp, 1),
                feels_like=round(raw.main.feels_like, 1),
                condition=condition,
                humidity_percent=raw.main.humidity,
                wind_speed_kmh=wind_kmh,
                visibility_km=visibility_km,
                is_travel_friendly=is_friendly,
                advisory=raw.to_travel_advisory(),
            )

        except httpx.HTTPStatusError as e:
            logger.warning(f"Weather API error for {city}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Weather service error for {city}: {e}")
            return None

    def travel_recommendation(
        self,
        origin: Optional[WeatherInfo],
        destination: Optional[WeatherInfo],
    ) -> str:
        """Generate a travel recommendation based on weather at both ends."""
        if not origin or not destination:
            return "Weather data unavailable for full recommendation."

        if not origin.is_travel_friendly or not destination.is_travel_friendly:
            return (
                f"⚠️ Caution advised. "
                f"{origin.city}: {origin.advisory} "
                f"{destination.city}: {destination.advisory}"
            )

        return (
            f"✅ Weather is suitable for travel. "
            f"{origin.city}: {origin.temperature_celsius}°C, {origin.condition}. "
            f"{destination.city}: {destination.temperature_celsius}°C, {destination.condition}."
        )