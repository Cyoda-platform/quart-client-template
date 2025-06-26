from datetime import datetime
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_weather_fetch_request(entity: dict):
    entity['status'] = 'processing'
    entity['requestedAt'] = datetime.utcnow().isoformat() + "Z"
    entity["workflowProcessed"] = True

async def process_validate_required_fields(entity: dict) -> bool:
    for field in ["latitude", "longitude", "parameters"]:
        if field not in entity:
            return True
    return False

async def process_validate_parameters_type(entity: dict) -> bool:
    parameters = entity.get("parameters")
    if not isinstance(parameters, list) or not all(isinstance(p, str) for p in parameters):
        return True
    return False

async def process_fetch_weather_data(entity: dict):
    try:
        latitude = entity["latitude"]
        longitude = entity["longitude"]
        parameters = entity["parameters"]
        start_date = entity.get("start_date")
        end_date = entity.get("end_date")

        weather_data = await fetch_weather_from_api(
            latitude=latitude,
            longitude=longitude,
            parameters=parameters,
            start_date=start_date,
            end_date=end_date
        )
        entity['status'] = 'completed'
        entity['data'] = weather_data
        entity['location'] = {"latitude": latitude, "longitude": longitude}
        entity['completedAt'] = datetime.utcnow().isoformat() + "Z"
        entity["workflowProcessed"] = True
    except Exception as e:
        entity['status'] = 'failed'
        entity['error'] = str(e)
        entity['completedAt'] = datetime.utcnow().isoformat() + "Z"
        entity["workflowProcessed"] = True
        logger.exception("Failed to fetch weather data in workflow")