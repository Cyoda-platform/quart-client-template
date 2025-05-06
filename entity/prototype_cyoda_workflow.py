from dataclasses import dataclass
from datetime import datetime
import logging
import uuid

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

OPENWEATHERMAP_API_KEY = "YOUR_OPENWEATHERMAP_API_KEY"  # TODO: Replace with your real API key
OPENWEATHERMAP_URL = "https://api.openweathermap.org/data/2.5/weather"


@dataclass
class Location:
    type: str  # e.g. "city", "coordinates", "zipcode"
    value: str  # e.g. "London", "51.5074,-0.1278", "90210"


@dataclass
class FetchWeatherRequest:
    location: Location
    parameters: list = None  # Optional list of requested data fields


async def fetch_weather_from_api(location_type: str, location_value: str, parameters: list):
    params = {"appid": OPENWEATHERMAP_API_KEY, "units": "metric"}

    if location_type == "city":
        params["q"] = location_value
    elif location_type == "coordinates":
        try:
            lat, lon = map(str.strip, location_value.split(","))
            params["lat"] = lat
            params["lon"] = lon
        except Exception:
            raise ValueError("Invalid coordinates format, expected 'lat,lon'")
    else:
        raise ValueError(f"Unsupported location type: {location_type}")

    async with httpx.AsyncClient() as client:
        resp = await client.get(OPENWEATHERMAP_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    result = {}
    main = data.get("main", {})
    wind = data.get("wind", {})
    weather = data.get("weather", [{}])[0]

    if not parameters:
        parameters = ["temperature", "humidity", "wind_speed", "forecast"]

    if "temperature" in parameters:
        result["temperature"] = main.get("temp")
    if "humidity" in parameters:
        result["humidity"] = main.get("humidity")
    if "wind_speed" in parameters:
        result["wind_speed"] = wind.get("speed")
    if "forecast" in parameters:
        result["forecast"] = weather.get("description")

    return result


async def process_entity_job(entity_data: dict):
    """
    Workflow function for entity_job entity.
    Fetches weather data, updates entity state, and adds supplementary 'entity_results' entity.
    """
    try:
        location = entity_data.get("location")
        parameters = entity_data.get("parameters", [])

        if not location or "type" not in location or "value" not in location:
            raise ValueError("Invalid location data")

        location_type = location["type"]
        location_value = location["value"]

        # Set initial state
        entity_data["status"] = "processing"
        entity_data["requestedAt"] = entity_data.get("requestedAt") or datetime.utcnow().isoformat() + "Z"
        entity_data["message"] = ""
        entity_data["persistedAt"] = datetime.utcnow().isoformat() + "Z"

        # Fetch weather data from external API
        weather_data = await fetch_weather_from_api(location_type, location_value, parameters)

        # Prepare supplementary entity_results entity
        # Use entity_data's technical_id if exists, else generate a new UUID as request_id for results
        request_id = entity_data.get("technical_id")
        if not request_id:
            # Generate a UUID for request_id and assign to entity_data for consistency
            request_id = str(uuid.uuid4())
            entity_data["technical_id"] = request_id

        result_entity = {
            "technical_id": request_id,  # Use same id for linking
            "request_id": request_id,
            "location": location,
            "data": weather_data,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "entity_version": ENTITY_VERSION
        }

        # Add supplementary entity_results entity
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="entity_results",
            entity_version=ENTITY_VERSION,
            entity=result_entity,
            workflow=None  # No workflow for results entity
        )

        # Update entity_job status to completed
        entity_data["status"] = "completed"
        entity_data["message"] = "Weather data fetched successfully"
        entity_data["completedAt"] = datetime.utcnow().isoformat() + "Z"

    except Exception as e:
        entity_data["status"] = "failed"
        entity_data["message"] = str(e)
        entity_data["completedAt"] = datetime.utcnow().isoformat() + "Z"
        logger.exception("Error in process_entity_job workflow")


@app.route("/weather/fetch", methods=["POST"])
@validate_request(FetchWeatherRequest)
async def fetch_weather(data: FetchWeatherRequest):
    # Compose initial entity_job data
    entity_data = {
        "location": {"type": data.location.type, "value": data.location.value},
        "parameters": data.parameters or [],
        "status": "pending",
        "requestedAt": datetime.utcnow().isoformat() + "Z",
        # technical_id is not set here; entity_service may generate it or workflow generates if missing
    }

    try:
        # Add entity_job with workflow function that will perform all async processing before persistence
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            entity=entity_data,
            workflow=process_entity_job
        )
        # Return the entity_id assigned by entity_service
        return jsonify({"request_id": entity_id, "status": "processing"}), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to register job"}), 500


@app.route("/weather/results/<string:request_id>", methods=["GET"])
async def get_weather_results(request_id):
    try:
        job = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            technical_id=request_id
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Request ID not found"}), 404

    if not job:
        return jsonify({"error": "Request ID not found"}), 404

    status = job.get("status")
    if status in ("processing", "pending"):
        return jsonify({"request_id": request_id, "status": "processing"}), 202

    if status == "failed":
        return jsonify({"request_id": request_id, "status": "failed", "message": job.get("message")}), 500

    try:
        result = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="entity_results",
            entity_version=ENTITY_VERSION,
            technical_id=request_id
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Results not found"}), 404

    if not result:
        return jsonify({"error": "Results not found"}), 404

    return jsonify(result)


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)