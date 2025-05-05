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

# In-memory store to mock persistence/cache
# Structure: {request_id: {status, requestedAt, location, data_type, weather_data, error_message}}
entity_jobs = {}

# Use OpenWeatherMap API (free tier)
# TODO: Replace with your own API key or configuration management
OPENWEATHER_API_KEY = "YOUR_OPENWEATHERMAP_API_KEY"
OPENWEATHER_API_URL = "https://api.openweathermap.org/data/2.5"

# Helper: build weather API url and params based on data_type
def build_openweather_url(location, data_type):
    params = {"appid": OPENWEATHER_API_KEY, "units": "metric"}

    if "city" in location and location["city"]:
        q = location["city"]
        params["q"] = q
    elif "latitude" in location and "longitude" in location:
        params["lat"] = location["latitude"]
        params["lon"] = location["longitude"]
    else:
        raise ValueError("Location must include either city or latitude+longitude")

    if data_type == "current":
        url = f"{OPENWEATHER_API_URL}/weather"
    elif data_type == "forecast":
        url = f"{OPENWEATHER_API_URL}/forecast"
    elif data_type == "historical":
        # OpenWeather free API does not support historical, so we fallback or mock
        # TODO: Implement historical data with paid API or alternative
        raise NotImplementedError("Historical data_type is not supported in prototype")
    else:
        raise ValueError(f"Unsupported data_type: {data_type}")

    return url, params


async def fetch_weather_data(location, data_type):
    url, params = build_openweather_url(location, data_type)
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.json()


async def process_entity(request_id, location, data_type):
    try:
        logger.info(f"Processing request {request_id} for location={location} data_type={data_type}")
        data = await fetch_weather_data(location, data_type)

        # TODO: Add any additional data processing/calculations here if needed

        entity_jobs[request_id]["weather_data"] = data
        entity_jobs[request_id]["status"] = "completed"
        logger.info(f"Completed request {request_id}")
    except NotImplementedError as nie:
        entity_jobs[request_id]["status"] = "failed"
        entity_jobs[request_id]["error_message"] = str(nie)
        logger.info(f"Request {request_id} failed: {nie}")
    except Exception as e:
        entity_jobs[request_id]["status"] = "failed"
        entity_jobs[request_id]["error_message"] = "Failed to fetch or process weather data."
        logger.exception(f"Exception processing request {request_id}: {e}")


@app.route("/weather/fetch", methods=["POST"])
async def fetch_weather():
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"message": "Missing JSON body"}), 400

        location = data.get("location")
        data_type = data.get("data_type")

        if not location or not isinstance(location, dict):
            return jsonify({"message": "Missing or invalid 'location' field"}), 400
        if not data_type or not isinstance(data_type, str):
            return jsonify({"message": "Missing or invalid 'data_type' field"}), 400

        # Validate location keys minimally
        if not (location.get("city") or (location.get("latitude") is not None and location.get("longitude") is not None)):
            return jsonify({"message": "Location must include 'city' or both 'latitude' and 'longitude'"}), 400

        request_id = str(uuid.uuid4())
        requested_at = datetime.utcnow().isoformat()

        entity_jobs[request_id] = {
            "status": "processing",
            "requestedAt": requested_at,
            "location": location,
            "data_type": data_type,
            "weather_data": None,
            "error_message": None,
        }

        # Fire and forget processing task
        asyncio.create_task(process_entity(request_id, location, data_type))

        return jsonify({"request_id": request_id, "status": "processing", "message": "Request accepted"}), 202

    except Exception as e:
        logger.exception(f"Exception in /weather/fetch endpoint: {e}")
        return jsonify({"message": "Internal server error"}), 500


@app.route("/weather/result/<request_id>", methods=["GET"])
async def get_weather_result(request_id):
    job = entity_jobs.get(request_id)
    if not job:
        return jsonify({"message": "Request ID not found"}), 404

    response = {
        "request_id": request_id,
        "location": job["location"],
        "data_type": job["data_type"],
        "status": job["status"],
    }

    if job["status"] == "completed":
        response["weather_data"] = job["weather_data"]
    elif job["status"] == "failed":
        response["error_message"] = job["error_message"]

    return jsonify(response)


if __name__ == '__main__':
    import sys
    import logging.config

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s - %(message)s'
    )

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```