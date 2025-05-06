from datetime import datetime
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

entity_job = {}  # job_id -> {status, requestedAt, message, ...}
entity_results = {}  # job_id -> weather data


async def process_fetch_weather(entity: dict):
    # Simulate fetching weather data without external API calls
    # We'll just create dummy data based on entity input
    location_type = entity.get('location', {}).get('type', '')
    location_value = entity.get('location', {}).get('value', '')
    parameters = entity.get('parameters') or []

    # Dummy weather data
    dummy_data = {
        "temperature": 20.5,
        "humidity": 65,
        "wind_speed": 5.5,
        "forecast": "Clear sky"
    }

    result = {}
    if not parameters:
        parameters = ["temperature", "humidity", "wind_speed", "forecast"]

    if "temperature" in parameters:
        result["temperature"] = dummy_data["temperature"]
    if "humidity" in parameters:
        result["humidity"] = dummy_data["humidity"]
    if "wind_speed" in parameters:
        result["wind_speed"] = dummy_data["wind_speed"]
    if "forecast" in parameters:
        result["forecast"] = dummy_data["forecast"]

    entity['weather_data'] = result


async def process_update_entity_status_success(entity: dict):
    entity_job_id = entity.get('request_id')
    if entity_job_id in entity_job:
        entity_job[entity_job_id]["status"] = "completed"
        entity_job[entity_job_id]["message"] = "Weather data fetched successfully"
        logger.info(f"Job {entity_job_id} completed successfully")


async def process_update_entity_status_failed(entity: dict, exc: Exception):
    entity_job_id = entity.get('request_id')
    if entity_job_id in entity_job:
        entity_job[entity_job_id]["status"] = "failed"
        entity_job[entity_job_id]["message"] = str(exc)
        logger.exception(f"Job {entity_job_id} failed")


async def process_store_results(entity: dict):
    entity_job_id = entity.get('request_id')
    if entity_job_id:
        entity_results[entity_job_id] = {
            "request_id": entity_job_id,
            "location": entity.get('location', {}),
            "data": entity.get('weather_data', {}),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }