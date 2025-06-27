import asyncio
from datetime import datetime
import uuid
import logging
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def fetch_weather_data(entity: dict):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": entity["latitude"],
        "longitude": entity["longitude"],
        "start_date": entity["start_date"],
        "end_date": entity["end_date"],
        "hourly": ",".join(entity["parameters"]),
        "timezone": "UTC",
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.exception(f"Failed to fetch weather data: {e}")
            raise

async def process_data(entity: dict):
    raw_data = entity.get("raw_data")
    if not raw_data:
        entity["status"] = "failed"
        entity["error"] = "No raw data to process"
        return
    hourly = raw_data.get("hourly", {})
    processed = {"dates": hourly.get("time", [])}
    for param in entity["parameters"]:
        processed[param] = hourly.get(param, [])
    entity["data"] = processed
    entity["workflowProcessed"] = True

async def process_entity(technical_id: str, entity: dict):
    try:
        raw_data = await fetch_weather_data(entity)
        entity["raw_data"] = raw_data
        entity["status"] = "completed"
        entity["completedAt"] = datetime.utcnow().isoformat()
        logger.info(f"Job {technical_id} completed successfully.")
    except Exception as e:
        entity["status"] = "failed"
        entity["error"] = str(e)
        logger.exception(f"Job {technical_id} failed.")

async def process_weather_fetch_request(entity: dict):
    entity["status"] = "processing"
    entity["createdAt"] = datetime.utcnow().isoformat()
    if "technical_id" not in entity or not entity["technical_id"]:
        entity["technical_id"] = str(uuid.uuid4())
    asyncio.create_task(process_entity(entity["technical_id"], entity.copy()))
    entity["workflowProcessed"] = True

async def status_is_failed(entity: dict) -> bool:
    return entity.get("status") == "failed"

async def status_is_completed(entity: dict) -> bool:
    return entity.get("status") == "completed"