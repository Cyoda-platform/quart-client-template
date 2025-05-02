from dataclasses import dataclass
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class ProcessData:
    city: str  # expecting city name to query weather

async def fetch_external_data(client: httpx.AsyncClient, city: str):
    """Fetch weather data for the given city from OpenWeatherMap API."""
    OPENWEATHER_API_KEY = "YOUR_OPENWEATHER_API_KEY"  # TODO: insert valid API key here
    OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"}
    try:
        response = await client.get(OPENWEATHER_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error when fetching weather data for city '{city}': {e.response.status_code}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error when fetching weather data for city '{city}': {e}")
        raise

async def process_entity_job(entity: dict) -> dict:
    """
    Workflow function applied asynchronously before persistence.
    This does the entire processing:
    - initialize status,
    - call external API,
    - process data,
    - update entity with final status and result.
    """
    try:
        entity["status"] = "processing"
        entity["requestedAt"] = datetime.utcnow().isoformat() + "Z"

        city = entity.get("city")
        if not city:
            raise ValueError("Missing 'city' attribute in entity")

        async with httpx.AsyncClient() as client:
            weather_data = await fetch_external_data(client, city)

        # Extract temperature in Celsius
        temp_celsius = weather_data.get("main", {}).get("temp")
        if temp_celsius is None:
            raise ValueError("Temperature data missing in API response")

        # Convert Celsius to Fahrenheit
        temp_fahrenheit = temp_celsius * 9 / 5 + 32

        weather_desc_list = weather_data.get("weather", [])
        weather_description = None
        if weather_desc_list and isinstance(weather_desc_list, list):
            weather_description = weather_desc_list[0].get("description")

        result = {
            "city": city,
            "temperature_celsius": temp_celsius,
            "temperature_fahrenheit": temp_fahrenheit,
            "weather_description": weather_description,
            "processedAt": datetime.utcnow().isoformat() + "Z",
        }

        entity["status"] = "completed"
        entity["result"] = result
        entity["completedAt"] = datetime.utcnow().isoformat() + "Z"

    except Exception as e:
        logger.exception("Exception in process_entity_job workflow")
        entity["status"] = "failed"
        entity["result"] = {"error": str(e)}
        entity["completedAt"] = datetime.utcnow().isoformat() + "Z"

    return entity

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@app.route("/process", methods=["POST"])
@validate_request(ProcessData)
async def post_process(data: ProcessData):
    """
    Just create the entity_job with city and let workflow function do the rest.
    """
    try:
        job_id = str(uuid.uuid4())
        # Compose initial entity with city and technical_id (job_id)
        entity = {
            "technical_id": job_id,
            "city": data.city
        }

        await entity_service.add_item(
            token=cyoda_token,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            entity=entity,
            workflow=process_entity_job
        )
        return jsonify({"processId": job_id, "status": "processing"}), 202

    except Exception as e:
        logger.exception("Failed to create job")
        return jsonify({"error": "Failed to create job"}), 500

@app.route("/result/<string:process_id>", methods=["GET"])
async def get_result(process_id):
    """Return processing status and result for the given process ID."""
    try:
        job = await entity_service.get_item(
            token=cyoda_token,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            technical_id=process_id
        )
    except Exception as e:
        logger.exception(f"Failed to get job {process_id}: {e}")
        return jsonify({"error": "Failed to retrieve job data"}), 500

    if not job:
        return jsonify({"error": "Process ID not found"}), 404

    response = {
        "processId": process_id,
        "status": job.get("status"),
        "result": job.get("result"),
    }
    return jsonify(response), 200

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)