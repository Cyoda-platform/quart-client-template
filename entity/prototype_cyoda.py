from dataclasses import dataclass
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# POST route - validation last due to quart-schema issue workaround
@dataclass
class ProcessData:
    city: str  # expecting city name to query weather


async def fetch_external_data(client: httpx.AsyncClient, city: str):
    """Fetch weather data for the given city from OpenWeatherMap API."""
    try:
        OPENWEATHER_API_KEY = "YOUR_OPENWEATHER_API_KEY"  # TODO: insert valid API key here
        OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
        params = {"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"}
        response = await client.get(OPENWEATHER_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        logger.exception(f"Failed to fetch external data: {e}")
        raise


async def process_entity(job_id: str, input_data: dict):
    """Process the job: call external API and perform calculations."""
    try:
        city = input_data.get("city")
        if not city:
            raise ValueError("Missing 'city' in inputData")

        async with httpx.AsyncClient() as client:
            weather_data = await fetch_external_data(client, city)

        # Example business logic: extract temperature and calculate a simple value
        temp = weather_data.get("main", {}).get("temp")
        if temp is None:
            raise ValueError("Temperature data missing in API response")

        # Example calculation: convert Celsius to Fahrenheit
        temp_fahrenheit = temp * 9 / 5 + 32

        result = {
            "city": city,
            "temperature_celsius": temp,
            "temperature_fahrenheit": temp_fahrenheit,
            "weather_description": weather_data.get("weather", [{}])[0].get("description"),
            "processedAt": datetime.utcnow().isoformat() + "Z",
        }

        # Update the entity_service item with completed status and result
        update_data = {
            "status": "completed",
            "result": result,
            "completedAt": datetime.utcnow().isoformat() + "Z",
        }
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            entity=update_data,
            technical_id=job_id,
            meta={}
        )

        logger.info(f"Job {job_id} completed successfully")

    except Exception as e:
        update_data = {
            "status": "failed",
            "result": {"error": str(e)},
            "completedAt": datetime.utcnow().isoformat() + "Z",
        }
        try:
            await entity_service.update_item(
                token=cyoda_token,
                entity_model="entity_job",
                entity_version=ENTITY_VERSION,
                entity=update_data,
                technical_id=job_id,
                meta={}
            )
        except Exception as ex:
            logger.exception(f"Failed to update job {job_id} status to failed: {ex}")
        logger.exception(f"Job {job_id} failed")


@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)


@app.route("/process", methods=["POST"])
@validate_request(ProcessData)
async def post_process(data: ProcessData):
    """Accept input data, start processing asynchronously, return job ID."""
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat() + "Z"
    initial_data = {"status": "processing", "requestedAt": requested_at}

    try:
        # Add item to entity_service, store job with job_id as technical_id
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            entity={"technical_id": job_id, **initial_data}
        )
    except Exception as e:
        logger.exception(f"Failed to add job {job_id}: {e}")
        return jsonify({"error": "Failed to create job"}), 500

    # Fire and forget the processing task
    asyncio.create_task(process_entity(job_id, data.__dict__))

    return jsonify({"processId": job_id, "status": "processing"}), 202


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