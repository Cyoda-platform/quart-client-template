from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class WeatherFetchRequest:
    latitude: float
    longitude: float
    parameters: List[str]

# In-memory async-safe cache for storing fetched weather data
entity_job: Dict[str, Dict[str, Any]] = {}
entity_job_lock = asyncio.Lock()

async def process_entity(data_id: str, latitude: float, longitude: float, parameters: list):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current_weather": "true",
        "hourly": ",".join(parameters),
        "timezone": "UTC",
    }

    logger.info(f"Fetching weather data for dataId={data_id}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            weather_data = response.json()

        async with entity_job_lock:
            entity_job[data_id].update({
                "status": "completed",
                "data": weather_data,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "latitude": latitude,
                "longitude": longitude,
                "parameters": parameters,
            })
        logger.info(f"Stored weather data for dataId={data_id}")
    except Exception as e:
        logger.exception(f"Error fetching dataId={data_id}: {e}")
        async with entity_job_lock:
            entity_job[data_id].update({
                "status": "failed",
                "error": str(e)
            })

@app.route("/weather/fetch", methods=["POST"])
# workaround: validation must come last on POST due to quart_schema defect
@validate_request(WeatherFetchRequest)
async def fetch_weather(data: WeatherFetchRequest):
    latitude = data.latitude
    longitude = data.longitude
    parameters = data.parameters

    data_id = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    async with entity_job_lock:
        entity_job[data_id] = {
            "status": "processing",
            "requestedAt": datetime.utcnow().isoformat() + "Z"
        }

    asyncio.create_task(process_entity(data_id, latitude, longitude, parameters))

    return jsonify({
        "status": "success",
        "message": "Weather data fetching started",
        "dataId": data_id
    })

@app.route("/weather/result/<data_id>", methods=["GET"])
async def get_weather_result(data_id):
    async with entity_job_lock:
        entry = entity_job.get(data_id)

    if not entry:
        return jsonify({"status": "error", "message": "dataId not found"}), 404
    if entry["status"] == "processing":
        return jsonify({"status": "processing", "message": "Data is still being fetched"}), 202
    if entry["status"] == "failed":
        return jsonify({"status": "error", "message": entry.get("error", "Unknown error")}), 500

    response = {
        "dataId": data_id,
        "latitude": entry.get("latitude"),
        "longitude": entry.get("longitude"),
        "parameters": {},
        "timestamp": entry.get("timestamp"),
    }

    data = entry.get("data", {})
    hourly = data.get("hourly", {})
    for param in entry.get("parameters", []):
        values = hourly.get(param)
        response["parameters"][param] = values[-1] if isinstance(values, list) else values

    return jsonify(response)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)