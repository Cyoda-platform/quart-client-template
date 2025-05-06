```python
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory mock persistence for jobs and results
entity_job = {}  # job_id -> {status, requestedAt, message}
entity_results = {}  # job_id -> weather data


OPENWEATHERMAP_API_KEY = "YOUR_OPENWEATHERMAP_API_KEY"  # TODO: Replace with your real API key
OPENWEATHERMAP_URL = "https://api.openweathermap.org/data/2.5/weather"


async def fetch_weather_from_api(location_type: str, location_value: str, parameters: list):
    """
    Call OpenWeatherMap API with location data.
    Supports 'city' and 'coordinates' location types.
    TODO: Extend with zipcode or other types if needed.
    """
    params = {"appid": OPENWEATHERMAP_API_KEY, "units": "metric"}

    if location_type == "city":
        params["q"] = location_value
    elif location_type == "coordinates":
        try:
            lat, lon = map(str.strip, location_value.split(","))
            params["lat"] = lat
            params["lon"] = lon
        except Exception as e:
            logger.exception("Invalid coordinates format")
            raise ValueError("Invalid coordinates format, expected 'lat,lon'")
    else:
        raise ValueError(f"Unsupported location type: {location_type}")

    async with httpx.AsyncClient() as client:
        resp = await client.get(OPENWEATHERMAP_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    # Extract requested parameters with fallback
    result = {}
    main = data.get("main", {})
    wind = data.get("wind", {})
    weather = data.get("weather", [{}])[0]

    if not parameters:
        # If no parameters specified, return all defaults
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


async def process_entity(job_id: str, data: dict):
    """
    Background task: fetch weather data, update job and results cache.
    """
    try:
        location_type = data["location"]["type"]
        location_value = data["location"]["value"]
        parameters = data.get("parameters", [])

        weather_data = await fetch_weather_from_api(location_type, location_value, parameters)

        entity_results[job_id] = {
            "request_id": job_id,
            "location": {"type": location_type, "value": location_value},
            "data": weather_data,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        entity_job[job_id]["status"] = "completed"
        entity_job[job_id]["message"] = "Weather data fetched successfully"
        logger.info(f"Job {job_id} completed successfully")
    except Exception as e:
        entity_job[job_id]["status"] = "failed"
        entity_job[job_id]["message"] = str(e)
        logger.exception(f"Job {job_id} failed")


@app.route("/weather/fetch", methods=["POST"])
async def fetch_weather():
    data = await request.get_json(force=True)
    job_id = str(uuid.uuid4())
    entity_job[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat() + "Z",
        "message": "",
    }

    # Fire and forget the processing task
    asyncio.create_task(process_entity(job_id, data))

    return jsonify({"request_id": job_id, "status": "processing"}), 202


@app.route("/weather/results/<string:request_id>", methods=["GET"])
async def get_weather_results(request_id):
    job = entity_job.get(request_id)
    if job is None:
        return jsonify({"error": "Request ID not found"}), 404

    if job["status"] == "processing":
        return jsonify({"request_id": request_id, "status": "processing"}), 202

    if job["status"] == "failed":
        return jsonify({"request_id": request_id, "status": "failed", "message": job.get("message")}), 500

    result = entity_results.get(request_id)
    if not result:
        # This should not happen if job is completed, but just in case
        return jsonify({"error": "Results not found"}), 404

    return jsonify(result)


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
