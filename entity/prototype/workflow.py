from datetime import datetime
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

async def process_prototype(entity: Dict[str, Any]) -> None:
    status = entity.get("status")
    if status not in [None, "none", "queued"]:
        return
    entity["status"] = "queued" if status in [None, "none"] else "processing"
    if entity["status"] == "processing":
        entity["processingStartedAt"] = datetime.utcnow().isoformat()
        await process_fetch_weather(entity)

async def is_status_failed(entity: Dict[str, Any]) -> bool:
    return entity.get("status") == "failed"

async def is_status_completed(entity: Dict[str, Any]) -> bool:
    return entity.get("status") == "completed"

async def process_fetch_weather(entity: Dict[str, Any]) -> None:
    input_params = entity.get("input", {})
    latitude = input_params.get("latitude")
    longitude = input_params.get("longitude")
    start_date = input_params.get("start_date")
    end_date = input_params.get("end_date")
    parameters = input_params.get("parameters", [])
    hourly = ",".join(parameters) if parameters else ""

    if latitude is None or longitude is None or not start_date or not end_date:
        entity["status"] = "failed"
        entity["errorMessage"] = "Missing required input parameters"
        entity["failedAt"] = datetime.utcnow().isoformat()
        return

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": hourly,
        "timezone": "auto",
    }

    try:
        external_data = await fetch_weather_external(params)
        hourly_data = external_data.get("hourly", {})
        timestamps = hourly_data.get("time", [])
        filtered_params: Dict[str, Any] = {}
        for param in parameters:
            filtered_params[param] = hourly_data.get(param, [])

        result = {
            "data_id": entity.get("technical_id") or entity.get("id") or "unknown",
            "latitude": latitude,
            "longitude": longitude,
            "parameters": filtered_params,
            "timestamps": timestamps,
        }

        entity["result"] = result
        entity["status"] = "completed"
        entity["completedAt"] = datetime.utcnow().isoformat()

    except Exception as e:
        logger.exception(f"Failed to fetch weather data in workflow for entity {entity.get('technical_id')}")
        entity["status"] = "failed"
        entity["result"] = None
        entity["errorMessage"] = str(e)
        entity["failedAt"] = datetime.utcnow().isoformat()