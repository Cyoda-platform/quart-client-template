from datetime import datetime
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_weather_fetch_request(entity: dict) -> dict:
    # Workflow orchestration only
    entity['status'] = 'processing'
    entity['requestedAt'] = datetime.utcnow().isoformat() + "Z"

    # Validate required fields
    missing_field = await process_validate_required_fields(entity)
    if missing_field:
        entity['status'] = 'failed'
        entity['error'] = f"Missing required field: {missing_field}"
        entity['completedAt'] = datetime.utcnow().isoformat() + "Z"
        return entity

    # Validate parameters type
    if not await process_validate_parameters_type(entity):
        entity['status'] = 'failed'
        entity['error'] = "Parameter 'parameters' must be a list of strings."
        entity['completedAt'] = datetime.utcnow().isoformat() + "Z"
        return entity

    # Fetch weather data from external API
    await process_fetch_weather_data(entity)

    return entity

async def process_validate_required_fields(entity: dict) -> str | None:
    # Return missing field name or None if all present
    for field in ["latitude", "longitude", "parameters"]:
        if field not in entity:
            return field
    return None

async def process_validate_parameters_type(entity: dict) -> bool:
    parameters = entity.get("parameters")
    if not isinstance(parameters, list) or not all(isinstance(p, str) for p in parameters):
        return False
    return True

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
    except Exception as e:
        entity['status'] = 'failed'
        entity['error'] = str(e)
        entity['completedAt'] = datetime.utcnow().isoformat() + "Z"
        logger.exception("Failed to fetch weather data in workflow")