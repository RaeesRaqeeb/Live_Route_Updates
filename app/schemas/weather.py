# app/schemas/weather.py
from pydantic import BaseModel
from typing import Optional


class WeatherCondition(BaseModel):
    id: int
    main: str
    description: str
    icon: str


class WeatherMain(BaseModel):
    temp: float
    feels_like: float
    temp_min: float
    temp_max: float
    pressure: int
    humidity: int


class WeatherWind(BaseModel):
    speed: float
    deg: Optional[int] = None


class WeatherVisibility(BaseModel):
    value: Optional[int] = None     # meters


class WeatherAPIResponse(BaseModel):
    """
    Raw response schema from OpenWeatherMap API.
    Maps directly to the API JSON response.
    """
    name: str
    weather: list[WeatherCondition]
    main: WeatherMain
    wind: WeatherWind
    visibility: Optional[int] = None
    dt: int                          # Unix timestamp

    def to_travel_advisory(self) -> str:
        """Generate a human-readable advisory based on conditions."""
        advisories = []
        if self.main.temp > 42:
            advisories.append("Extreme heat — carry water and avoid midday travel.")
        if self.main.temp < 2:
            advisories.append("Near-freezing temperatures — risk of black ice.")
        if self.main.humidity > 90:
            advisories.append("Very high humidity — possible fog or mist on roads.")
        if self.wind.speed > 15:
            advisories.append("Strong winds — caution for high-sided vehicles.")
        vis = self.visibility or 10000
        if vis < 1000:
            advisories.append("Poor visibility — slow down and use headlights.")
        return " ".join(advisories) if advisories else "Conditions are suitable for travel."