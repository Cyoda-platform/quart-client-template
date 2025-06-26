import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Any, List
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
import httpx
import uuid

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class FetchRequest:
    latitude: float
    longitude: float
    parameters: List[str]
    start_date: str
    end_date: str

# In-memory cache for prototype persistence
entity_job: Dict[str, Dict[str, Any]] = {}

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

async def fetch_weather_external(params: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(OPEN_METEO_URL, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.exception(f"HTTP error when calling Open-Meteo API: {e}")
            raise

async def process_entity_job(data_id: str):
    job = entity_job.get(data_id)
    if not job:
        logger.error(f"Unknown data_id {data_id}")
        return

    job["status"] = "processing"
    input_params = job["input"]
    latitude = input_params["latitude"]
    longitude = input_params["longitude"]
    start_date = input_params["start_date"]
    end_date = input_params["end_date"]
    parameters = input_params.get("parameters", [])
    hourly = ",".join(parameters) if parameters else ""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": hourly,
        "timezone": "auto",
    }

    try:
        external_data = await fetch_weather_external(params)
        hourly_data = external_data.get("hourly", {})
        timestamps = hourly_data.get("time", [])
        filtered_params: Dict[str, Any] = {}
        for param in parameters:
            filtered_params[param] = hourly_data.get(param, [])
        result = {
            "data_id": data_id,
            "latitude": latitude,
            "longitude": longitude,
            "parameters": filtered_params,
            "timestamps": timestamps,
        }
        job["result"] = result
        job["status"] = "completed"
        logger.info(f"Completed data_id {data_id}")
    except Exception as e:
        job["status"] = "failed"
        job["result"] = None
        logger.exception(f"Failed data_id {data_id}: {e}")

@app.route("/weather/fetch", methods=["POST"])
@validate_request(FetchRequest)  # workaround: validate_request last for POST
async def fetch_weather(data: FetchRequest):
    data_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()
    entity_job[data_id] = {
        "status": "queued",
        "requestedAt": requested_at,
        "input": data.__dict__,
        "result": None,
    }
    asyncio.create_task(process_entity_job(data_id))
    return jsonify({
        "status": "success",
        "message": "Weather data fetch initiated",
        "data_id": data_id,
    })

@app.route("/weather/result/<data_id>", methods=["GET"])
async def get_weather_result(data_id: str):
    job = entity_job.get(data_id)
    if not job:
        return jsonify({"status": "error", "message": "Data ID not found"}), 404
    if job["status"] in ("queued", "processing"):
        return jsonify({"status": "processing", "message": "Data is being fetched"}), 202
    if job["status"] == "failed":
        return jsonify({"status": "failed", "message": "Failed to fetch weather data"}), 500
    return jsonify(job["result"])

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)