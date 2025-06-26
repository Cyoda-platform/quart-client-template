from datetime import datetime
import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_fetch_data(entity: Dict[str, Any]) -> None:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": entity.get("latitude"),
        "longitude": entity.get("longitude"),
        "hourly": ",".join(entity.get("parameters", [])),
        "timezone": "UTC",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        entity["data"] = data
        entity["timestamp"] = datetime.utcnow().isoformat() + "Z"
        entity["status"] = "completed"
        if "error" in entity:
            del entity["error"]
        logger.info(f"Weather data fetched successfully for entity at {entity['timestamp']}")

    except httpx.RequestError as e:
        error_message = f"Network error while fetching weather data: {str(e)}"
        entity["status"] = "failed"
        entity["error"] = error_message
        logger.error(error_message)

    except httpx.HTTPStatusError as e:
        error_message = f"HTTP error while fetching weather data: {str(e)}"
        entity["status"] = "failed"
        entity["error"] = error_message
        logger.error(error_message)

    except Exception as e:
        error_message = f"Unexpected error while fetching weather data: {str(e)}"
        entity["status"] = "failed"
        entity["error"] = error_message
        logger.error(error_message)

async def process_validate_input(entity: Dict[str, Any]) -> None:
    latitude = entity.get("latitude")
    longitude = entity.get("longitude")
    parameters = entity.get("parameters", [])

    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        entity["status"] = "failed"
        entity["error"] = "Invalid latitude or longitude"
        logger.error("Invalid latitude or longitude in entity")
        return

    if not parameters or not all(isinstance(p, str) for p in parameters):
        entity["status"] = "failed"
        entity["error"] = "Parameters must be a non-empty list of strings"
        logger.error("Invalid parameters in entity")
        return

async def process_weather_fetch_request(entity: Dict[str, Any]) -> None:
    entity["status"] = "processing"
    entity["requestedAt"] = entity.get("requestedAt") or datetime.utcnow().isoformat() + "Z"

    await process_validate_input(entity)
    if entity.get("status") == "failed":
        return

    await process_fetch_data(entity)