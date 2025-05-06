from dataclasses import dataclass
from datetime import datetime
import logging
import uuid

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

entity_job = {}  # job_id -> {status, requestedAt, message, ...}
entity_results = {}  # job_id -> weather data

OPENWEATHERMAP_API_KEY = "YOUR_OPENWEATHERMAP_API_KEY"  # TODO: Replace with your real API key
OPENWEATHERMAP_URL = "https://api.openweathermap.org/data/2.5/weather"


@dataclass
class Location:
    type: str
    value: str


@dataclass
class FetchWeatherRequest:
    location: Location
    parameters: list = None


async def process_fetch_weather(entity: dict):
    # extract parameters for API call
    location_type = entity['location'].type
    location_value = entity['location'].value
    parameters = entity.get('parameters') or []

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

    main = data.get("main", {})
    wind = data.get("wind", {})
    weather = data.get("weather", [{}])[0]

    result = {}
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

    entity['weather_data'] = result


async def process_update_entity_status_success(entity: dict):
    entity_job_id = entity['request_id']
    entity_job[entity_job_id]["status"] = "completed"
    entity_job[entity_job_id]["message"] = "Weather data fetched successfully"
    logger.info(f"Job {entity_job_id} completed successfully")


async def process_update_entity_status_failed(entity: dict, exc: Exception):
    entity_job_id = entity['request_id']
    entity_job[entity_job_id]["status"] = "failed"
    entity_job[entity_job_id]["message"] = str(exc)
    logger.exception(f"Job {entity_job_id} failed")


async def process_store_results(entity: dict):
    entity_job_id = entity['request_id']
    entity_results[entity_job_id] = {
        "request_id": entity_job_id,
        "location": {"type": entity['location'].type, "value": entity['location'].value},
        "data": entity['weather_data'],
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


async def process_entity(entity: dict):
    try:
        await process_fetch_weather(entity)
        await process_store_results(entity)
        await process_update_entity_status_success(entity)
    except Exception as e:
        await process_update_entity_status_failed(entity, e)


@app.route("/weather/fetch", methods=["POST"])
@validate_request(FetchWeatherRequest)  # validation last in POST (issue workaround)
async def fetch_weather(data: FetchWeatherRequest):
    job_id = str(uuid.uuid4())
    entity_job[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat() + "Z",
        "message": "",
    }

    entity = {
        "request_id": job_id,
        "location": data.location,
        "parameters": data.parameters,
    }

    asyncio.create_task(process_entity(entity))

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
        return jsonify({"error": "Results not found"}), 404

    return jsonify(result)


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)