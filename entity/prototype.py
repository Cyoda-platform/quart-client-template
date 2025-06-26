import asyncio
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Request dataclass for POST /weather/fetch
@dataclass
class WeatherFetchRequest:
    latitude: float
    longitude: float
    parameters: List[str]
    start_date: str
    end_date: str

# In-memory cache for prototype: job_id -> job data and results
entity_job: Dict[str, Dict] = {}

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

async def fetch_weather_data(latitude, longitude, parameters, start_date, end_date):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(parameters),
        "timezone": "auto",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(OPEN_METEO_URL, params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.exception(f"Error while calling Open-Meteo API: {e}")
            raise

async def process_entity(job_id: str, data: WeatherFetchRequest):
    try:
        raw_weather = await fetch_weather_data(
            data.latitude, data.longitude, data.parameters, data.start_date, data.end_date
        )
        hourly_data = raw_weather.get("hourly", {})
        filtered_data = {param: hourly_data.get(param, []) for param in data.parameters}
        entity_job[job_id].update(
            {
                "status": "completed",
                "result": {
                    "request_id": job_id,
                    "latitude": data.latitude,
                    "longitude": data.longitude,
                    "data": filtered_data,
                    "date_range": {"start": data.start_date, "end": data.end_date},
                },
                "completedAt": datetime.utcnow().isoformat() + "Z",
            }
        )
        logger.info(f"Job {job_id} completed successfully")
    except Exception as e:
        entity_job[job_id].update({"status": "failed", "error": str(e)})
        logger.exception(f"Job {job_id} failed")

@app.route("/weather/fetch", methods=["POST"])
@validate_request(WeatherFetchRequest)  # workaround: validation last for POST due to quart-schema issue
async def weather_fetch(data: WeatherFetchRequest):
    request_id = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    entity_job[request_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat() + "Z",
    }
    asyncio.create_task(process_entity(request_id, data))
    return jsonify(
        {
            "status": "success",
            "message": "Weather data fetch initiated",
            "request_id": request_id,
        }
    )

@app.route("/weather/result/<request_id>", methods=["GET"])
async def weather_result(request_id: str):
    job = entity_job.get(request_id)
    if not job:
        return jsonify({"status": "error", "message": "Request ID not found"}), 404
    if job["status"] == "processing":
        return jsonify({"status": "processing", "message": "Data is still being fetched"}), 202
    if job["status"] == "failed":
        return jsonify({"status": "failed", "message": job.get("error", "Unknown error")}), 500
    return jsonify(job["result"])

if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)