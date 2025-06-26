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

async def process_validate_input(entity: dict) -> bool:
    try:
        _ = entity["latitude"]
        _ = entity["longitude"]
        _ = entity["parameters"]
        _ = entity["start_date"]
        _ = entity["end_date"]
        return False if (entity.get("latitude") is None or entity.get("longitude") is None or not entity.get("parameters") or not entity.get("start_date") or not entity.get("end_date")) else True
    except KeyError as e:
        entity["status"] = "failed"
        entity["error"] = f"Missing required field: {e.args[0]}"
        logger.error(entity["error"])
        return False

async def process_weather_fetch(entity: dict):
    is_valid = await process_validate_input(entity)
    if not is_valid:
        entity["status"] = "failed"
        entity["workflowProcessed"] = True
        return entity

    entity["status"] = "processing"
    entity["requestedAt"] = datetime.utcnow().isoformat() + "Z"
    entity["workflowProcessed"] = True

    return entity

async def process_fetch_data(entity: dict):
    latitude = entity["latitude"]
    longitude = entity["longitude"]
    parameters = entity["parameters"]
    start_date = entity["start_date"]
    end_date = entity["end_date"]
    raw_weather = await fetch_weather_data(latitude, longitude, parameters, start_date, end_date)
    entity["raw_weather"] = raw_weather
    entity["workflowProcessed"] = True
    return entity

async def process_filter_data(entity: dict):
    raw_weather = entity.get("raw_weather", {})
    hourly_data = raw_weather.get("hourly", {})
    filtered_data = {param: hourly_data.get(param, []) for param in entity.get("parameters", [])}
    entity["filtered_data"] = filtered_data
    entity["result"] = {
        "latitude": entity.get("latitude"),
        "longitude": entity.get("longitude"),
        "data": filtered_data,
        "date_range": {"start": entity.get("start_date"), "end": entity.get("end_date")},
    }
    entity["status"] = "completed"
    entity["completedAt"] = datetime.utcnow().isoformat() + "Z"
    entity.pop("error", None)
    entity["workflowProcessed"] = True
    return entity