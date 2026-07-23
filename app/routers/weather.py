# app/routers/weather.py
from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.weather_service import WeatherService
from app.core.dependencies import get_weather_service
from app.schemas.response import APIResponse, WeatherInfo

router = APIRouter()


@router.get("/weather/{city}", response_model=APIResponse)
async def get_city_weather(
    city: str,
    weather_service: WeatherService = Depends(get_weather_service),
):
    """
    Get current weather for any Pakistani city.
    Example: GET /api/v1/weather/Lahore
    """
    try:
        weather = await weather_service.get_weather(city)
        if not weather:
            raise HTTPException(status_code=404, detail=f"Weather data not found for '{city}'")
        return APIResponse.ok(weather, f"Weather for {city}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weather/compare/", response_model=APIResponse)
async def compare_weather(
    origin: str = Query(..., description="Origin city"),
    destination: str = Query(..., description="Destination city"),
    weather_service: WeatherService = Depends(get_weather_service),
):
    """
    Compare weather between two cities.
    Example: GET /api/v1/weather/compare/?origin=Lahore&destination=Islamabad
    """
    try:
        origin_weather = await weather_service.get_weather(origin)
        dest_weather   = await weather_service.get_weather(destination)

        return APIResponse.ok(
            {
                "origin": origin_weather,
                "destination": dest_weather,
                "recommendation": weather_service.travel_recommendation(
                    origin_weather, dest_weather
                ),
            },
            "Weather comparison ready",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))