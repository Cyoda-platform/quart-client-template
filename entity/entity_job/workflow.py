import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@dataclass
class Location:
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

def build_openweather_url(location: Location, data_type: str):
    params = {"appid": "YOUR_OPENWEATHERMAP_API_KEY", "units": "metric"}

    if location.city:
        params["q"] = location.city
    elif location.latitude is not None and location.longitude is not None:
        params["lat"] = location.latitude
        params["lon"] = location.longitude
    else:
        raise ValueError("Location must include either city or latitude+longitude")

    if data_type == "current":
        url = "https://api.openweathermap.org/data/2.5/weather"
    elif data_type == "forecast":
        url = "https://api.openweathermap.org/data/2.5/forecast"
    elif data_type == "historical":
        # Historical data not supported here
        raise NotImplementedError("Historical data_type is not supported")
    else:
        raise ValueError(f"Unsupported data_type: {data_type}")

    return url, params

async def process_fetch_weather_data(entity: dict):
    location_dict = entity.get("location", {})
    data_type = entity.get("data_type")

    location = Location(
        city=location_dict.get("city"),
        latitude=location_dict.get("latitude"),
        longitude=location_dict.get("longitude"),
    )

    url, params = build_openweather_url(location, data_type)
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.json()

async def process_update_entity_success(entity: dict, weather_data: dict):
    entity["status"] = "completed"
    entity["requestedAt"] = datetime.utcnow().isoformat()
    entity["weather_data"] = weather_data
    entity["error_message"] = None

async def process_update_entity_failure(entity: dict, error_message: str):
    entity["status"] = "failed"
    entity["requestedAt"] = datetime.utcnow().isoformat()
    entity["weather_data"] = None
    entity["error_message"] = error_message