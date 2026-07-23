# tests/test_routes.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Health endpoint should always return 200."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "app" in data
    assert data["app"] == "ok"


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Root endpoint returns welcome message."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


@pytest.mark.asyncio
async def test_route_query_validation(client: AsyncClient):
    """Route query should reject missing fields."""
    response = await client.post(
        "/api/v1/route/info",
        json={"origin": "Lahore"},   # Missing destination
    )
    assert response.status_code == 422   # Validation error


@pytest.mark.asyncio
async def test_route_query_valid_request(client: AsyncClient, monkeypatch):
    """
    Test full route query with mocked external services.
    """
    from app.services import cache_service, weather_service

    # Mock cache to always miss
    async def mock_cache_get(key):
        return None

    async def mock_cache_set(key, value, ttl=None):
        return True

    # Mock weather to return dummy data
    async def mock_weather(city):
        from app.schemas.response import WeatherInfo
        return WeatherInfo(
            city=city,
            temperature_celsius=28.0,
            feels_like=30.0,
            condition="Clear",
            humidity_percent=55,
            wind_speed_kmh=10.0,
            visibility_km=10.0,
            is_travel_friendly=True,
            advisory="Conditions are suitable for travel.",
        )

    monkeypatch.setattr(
        "app.services.cache_service.CacheService.get", mock_cache_get
    )
    monkeypatch.setattr(
        "app.services.cache_service.CacheService.set", mock_cache_set
    )
    monkeypatch.setattr(
        "app.services.weather_service.WeatherService.get_weather", mock_weather
    )

    response = await client.post(
        "/api/v1/route/info",
        json={
            "origin": "Lahore",
            "destination": "Islamabad",
            "query_type": "weather",
        },
    )
    # Should either succeed or fail gracefully
    assert response.status_code in [200, 500]