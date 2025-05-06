import logging
import uuid
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

OPENWEATHER_API_KEY = "your_openweathermap_api_key"  # Replace with your actual key
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"


async def process_fetch_current_weather(entity):
    location = entity.get("location", {})
    params = {"appid": OPENWEATHER_API_KEY, "units": "metric"}

    if location.get("city"):
        params["q"] = location["city"]
    elif location.get("latitude") is not None and location.get("longitude") is not None:
        params["lat"] = location["latitude"]
        params["lon"] = location["longitude"]
    else:
        raise ValueError("Location must have either city or latitude & longitude")

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{OPENWEATHER_BASE_URL}/weather", params=params)
        resp.raise_for_status()
        entity['weather_data'] = resp.json()


async def process_fetch_forecast_weather(entity):
    location = entity.get("location", {})
    params = {"appid": OPENWEATHER_API_KEY, "units": "metric"}

    if location.get("city"):
        params["q"] = location["city"]
    elif location.get("latitude") is not None and location.get("longitude") is not None:
        params["lat"] = location["latitude"]
        params["lon"] = location["longitude"]
    else:
        raise ValueError("Location must have either city or latitude & longitude")

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{OPENWEATHER_BASE_URL}/forecast", params=params)
        resp.raise_for_status()
        entity['weather_data'] = resp.json()