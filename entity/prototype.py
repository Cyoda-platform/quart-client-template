from dataclasses import dataclass
from typing import Optional, Union

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

# In-memory store to mock persistence/cache
# Structure: {request_id: {status, requestedAt, location, data_type, weather_data, error_message}}
entity_jobs = {}

# Use OpenWeatherMap API (free tier)
# TODO: Replace with your own API key or configuration management
OPENWEATHER_API_KEY = "YOUR_OPENWEATHERMAP_API_KEY"
OPENWEATHER_API_URL = "https://api.openweathermap.org/data/2.5"

@dataclass
class Location:
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

@dataclass
class FetchWeatherRequest:
    location: Location
    data_type: str  # "current", "forecast", or "historical"


# Helper: build weather API url and params based on data_type
def build_openweather_url(location: Location, data_type: str):
    params = {"appid": OPENWEATHER_API_KEY, "units": "metric"}

    if location.city:
        params["q"] = location.city
    elif location.latitude is not None and location.longitude is not None:
        params["lat"] = location.latitude
        params["lon"] = location.longitude
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


async def fetch_weather_data(location: Location, data_type: str):
    url, params = build_openweather_url(location, data_type)
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.json()


async def process_entity(request_id: str, location: Location, data_type: str):
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
@validate_request(FetchWeatherRequest)  # Put last in POST route per quart-schema issue workaround
async def fetch_weather(data: FetchWeatherRequest):
    try:
        location = data.location
        data_type = data.data_type

        # Validate location keys minimally
        if not (location.city or (location.latitude is not None and location.longitude is not None)):
            return jsonify({"message": "Location must include 'city' or both 'latitude' and 'longitude'"}), 400

        request_id = str(uuid.uuid4())
        requested_at = datetime.utcnow().isoformat()

        entity_jobs[request_id] = {
            "status": "processing",
            "requestedAt": requested_at,
            "location": {
                "city": location.city,
                "latitude": location.latitude,
                "longitude": location.longitude,
            },
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


# No request parameters for GET, so no validation needed
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