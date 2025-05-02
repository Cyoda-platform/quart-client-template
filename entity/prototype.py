from dataclasses import dataclass
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory local cache to mock persistence
entity_job = {}

# Example external API endpoint for demonstration (real API)
# Using OpenWeatherMap Current Weather API as a sample external API
# TODO: Replace with actual API key or another API if needed
OPENWEATHER_API_KEY = "YOUR_OPENWEATHER_API_KEY"  # TODO: insert valid API key here
OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"

@dataclass
class ProcessData:
    city: str  # expecting city name to query weather


async def fetch_external_data(client: httpx.AsyncClient, city: str):
    """Fetch weather data for the given city from OpenWeatherMap API."""
    try:
        params = {"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"}
        response = await client.get(OPENWEATHER_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        logger.exception(f"Failed to fetch external data: {e}")
        raise


async def process_entity(entity_job: dict, job_id: str, input_data: dict):
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

        # Update job with completed status and result
        entity_job[job_id]["status"] = "completed"
        entity_job[job_id]["result"] = result
        entity_job[job_id]["completedAt"] = datetime.utcnow().isoformat() + "Z"

        logger.info(f"Job {job_id} completed successfully")

    except Exception as e:
        entity_job[job_id]["status"] = "failed"
        entity_job[job_id]["result"] = {"error": str(e)}
        entity_job[job_id]["completedAt"] = datetime.utcnow().isoformat() + "Z"
        logger.exception(f"Job {job_id} failed")

# POST route - validation last due to quart-schema issue workaround
@app.route("/process", methods=["POST"])
@validate_request(ProcessData)
async def post_process(data: ProcessData):
    """Accept input data, start processing asynchronously, return job ID."""
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat() + "Z"
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}

    # Fire and forget the processing task
    asyncio.create_task(process_entity(entity_job, job_id, data.__dict__))

    return jsonify({"processId": job_id, "status": "processing"}), 202

# GET route - validation first due to quart-schema issue workaround
@app.route("/result/<string:process_id>", methods=["GET"])
async def get_result(process_id):
    """Return processing status and result for the given process ID."""
    job = entity_job.get(process_id)
    if not job:
        return jsonify({"error": "Process ID not found"}), 404

    response = {
        "processId": process_id,
        "status": job["status"],
        "result": job.get("result"),
    }
    return jsonify(response), 200


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
