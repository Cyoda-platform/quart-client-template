import asyncio
import uuid
from datetime import datetime
import httpx
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MSC_GEOMET_BASE_URL = "https://api.meteo.lt/v1"

async def process_entity_job(entity):
    # Workflow orchestration only
    if "requestedAt" not in entity:
        entity["requestedAt"] = datetime.utcnow().isoformat() + "Z"
    entity["status"] = "queued"
    if not entity.get("technical_id"):
        entity["technical_id"] = str(uuid.uuid4())
    if not entity.get("location") or not entity.get("parameters"):
        entity["status"] = "error"
        entity["error"] = "Missing required fields: location and parameters"
        return entity
    asyncio.create_task(process_fetch_data(entity))
    return entity

async def process_fetch_data(entity):
    entity["status"] = "processing"
    try:
        data = await process_fetch_weather(entity)
        if data is None:
            entity["status"] = "error"
            entity["error"] = "Failed to fetch data from MSC GeoMet"
            entity["result"] = {}
        else:
            entity["status"] = "completed"
            entity["result"] = {
                "location": entity.get("location"),
                "parameters": data,
                "date": entity.get("date") or datetime.utcnow().strftime("%Y-%m-%d"),
                "retrieved_at": datetime.utcnow().isoformat() + "Z",
            }
    except Exception as e:
        logger.exception(e)
        entity["status"] = "error"
        entity["error"] = str(e)
        entity["result"] = {}

async def process_fetch_weather(entity):
    location = entity.get("location")
    parameters = entity.get("parameters", [])
    date = entity.get("date")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            url = f"{MSC_GEOMET_BASE_URL}/places/{location}/forecasts/long-term"
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            forecasts = data.get("forecastTimestamps", [])
            if not forecasts:
                return {}
            forecast = forecasts[0]
            extracted = {}
            if "temperature" in parameters and "airTemperature" in forecast:
                extracted["temperature"] = forecast["airTemperature"]
            if "humidity" in parameters and "relativeHumidity" in forecast:
                extracted["humidity"] = forecast["relativeHumidity"]
            if "wind_speed" in parameters and "windSpeed" in forecast:
                extracted["wind_speed"] = forecast["windSpeed"]
            return extracted
        except Exception as e:
            logger.exception(f"Error fetching weather from MSC GeoMet: {e}")
            return None