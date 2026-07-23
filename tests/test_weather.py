# tests/test_weather.py
import pytest
from unittest.mock import AsyncMock, patch
from app.services.weather_service import WeatherService
from app.schemas.response import WeatherInfo


@pytest.fixture
def weather_service():
    return WeatherService()


@pytest.fixture
def mock_weather_response():
    return {
        "name": "Lahore",
        "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
        "main": {
            "temp": 32.5,
            "feels_like": 35.0,
            "temp_min": 28.0,
            "temp_max": 36.0,
            "pressure": 1010,
            "humidity": 60,
        },
        "wind": {"speed": 3.5, "deg": 180},
        "visibility": 10000,
        "dt": 1700000000,
    }


@pytest.mark.asyncio
async def test_get_weather_success(weather_service, mock_weather_response):
    """Test successful weather fetch and transformation."""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_weather_response
        mock_response.raise_for_status = lambda: None
        mock_get.return_value = mock_response

        result = await weather_service.get_weather("Lahore")

        assert result is not None
        assert isinstance(result, WeatherInfo)
        assert result.city == "Lahore"
        assert result.temperature_celsius == 32.5
        assert result.humidity_percent == 60


@pytest.mark.asyncio
async def test_get_weather_city_not_found(weather_service):
    """Test that invalid city returns None gracefully."""
    with patch("httpx.AsyncClient.get") as mock_get:
        import httpx
        mock_get.side_effect = httpx.HTTPStatusError(
            "Not found",
            request=AsyncMock(),
            response=AsyncMock(status_code=404),
        )
        result = await weather_service.get_weather("FakeCity123")
        assert result is None


def test_travel_recommendation_both_safe(weather_service):
    """Both cities safe → positive recommendation."""
    origin = WeatherInfo(
        city="Lahore", temperature_celsius=28, feels_like=30,
        condition="Clear", humidity_percent=50, wind_speed_kmh=10,
        visibility_km=10, is_travel_friendly=True, advisory="Good conditions."
    )
    dest = WeatherInfo(
        city="Islamabad", temperature_celsius=25, feels_like=26,
        condition="Partly Cloudy", humidity_percent=55, wind_speed_kmh=12,
        visibility_km=9, is_travel_friendly=True, advisory="Good conditions."
    )
    result = weather_service.travel_recommendation(origin, dest)
    assert "✅" in result


def test_travel_recommendation_one_unsafe(weather_service):
    """One unsafe city → caution message."""
    origin = WeatherInfo(
        city="Lahore", temperature_celsius=45, feels_like=48,
        condition="Hot", humidity_percent=80, wind_speed_kmh=5,
        visibility_km=10, is_travel_friendly=False, advisory="Extreme heat."
    )
    dest = WeatherInfo(
        city="Islamabad", temperature_celsius=25, feels_like=26,
        condition="Clear", humidity_percent=50, wind_speed_kmh=8,
        visibility_km=10, is_travel_friendly=True, advisory="Good."
    )
    result = weather_service.travel_recommendation(origin, dest)
    assert "⚠️" in result