import logging
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)

async def fetch_weather_data(latitude, longitude, parameters, start_date, end_date):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(parameters),
        "timezone": "auto",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get("https://api.open-meteo.com/v1/forecast", params=params)
        resp.raise_for_status()
        return resp.json()

async def process_validate_input(entity: dict):
    try:
        _ = entity["latitude"]
        _ = entity["longitude"]
        _ = entity["parameters"]
        _ = entity["start_date"]
        _ = entity["end_date"]
        return True
    except KeyError as e:
        entity["status"] = "failed"
        entity["error"] = f"Missing required field: {e.args[0]}"
        logger.error(entity["error"])
        return False

async def process_fetch_data(entity: dict):
    latitude = entity["latitude"]
    longitude = entity["longitude"]
    parameters = entity["parameters"]
    start_date = entity["start_date"]
    end_date = entity["end_date"]
    raw_weather = await fetch_weather_data(latitude, longitude, parameters, start_date, end_date)
    return raw_weather

async def process_filter_data(entity: dict, raw_weather: dict):
    hourly_data = raw_weather.get("hourly", {})
    filtered_data = {param: hourly_data.get(param, []) for param in entity["parameters"]}
    return filtered_data

async def process_weather_fetch(entity: dict):
    if not await process_validate_input(entity):
        return entity

    entity["status"] = "processing"
    entity["requestedAt"] = datetime.utcnow().isoformat() + "Z"

    try:
        raw_weather = await process_fetch_data(entity)
        filtered_data = await process_filter_data(entity, raw_weather)

        entity["status"] = "completed"
        entity["result"] = {
            "latitude": entity["latitude"],
            "longitude": entity["longitude"],
            "data": filtered_data,
            "date_range": {"start": entity["start_date"], "end": entity["end_date"]},
        }
        entity["completedAt"] = datetime.utcnow().isoformat() + "Z"
        entity.pop("error", None)
    except Exception:
        logger.exception("Error fetching weather data in workflow")
        entity["status"] = "failed"
        entity["error"] = "Error fetching weather data"
    return entity