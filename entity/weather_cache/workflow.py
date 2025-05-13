import logging
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)

async def process_weather_cache(entity: dict) -> dict:
    # Workflow orchestration only
    await process_validate_location(entity)
    await process_fetch_weather(entity)
    await process_update_timestamps(entity)
    return entity

async def process_validate_location(entity: dict):
    lat = entity.get("latitude")
    lon = entity.get("longitude")
    if lat is None or lon is None:
        logger.warning("process_validate_location: latitude or longitude missing in entity")
        entity["fetch_error"] = "Missing latitude or longitude"
        # Stop workflow by raising
        raise ValueError("Missing latitude or longitude")

async def process_fetch_weather(entity: dict):
    lat = entity.get("latitude")
    lon = entity.get("longitude")
    try:
        data = await fetch_weather_data(lat, lon)
        entity["data"] = data
        entity.pop("fetch_error", None)  # Clear fetch errors on success
        logger.info(f"Weather data fetched and updated for ({lat}, {lon})")
    except Exception as e:
        logger.exception(f"Failed to fetch weather data in process_fetch_weather: {e}")
        entity["fetch_error"] = str(e)

async def process_update_timestamps(entity: dict):
    now = datetime.utcnow().isoformat() + "Z"
    entity["timestamp"] = now
    entity["processed_at"] = now

async def fetch_weather_data(lat: float, lon: float) -> dict:
    # TODO: Implement actual fetch logic or mock
    async with httpx.AsyncClient() as client:
        # Example placeholder URL and parameters - replace with real MSC GeoMet API details
        url = "https://api.msc-geomet.com/weather"
        params = {"lat": lat, "lon": lon}
        resp = await client.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()