import asyncio
import logging
from datetime import datetime
from typing import List
from dataclasses import dataclass

import httpx
from quart import Quart, jsonify, request
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
    start_date: str
    end_date: str

# workaround: quart-schema defect requires validate_request after route decorator for POST
@app.route("/weather/fetch", methods=["POST"])
@validate_request(WeatherFetchRequest)
async def weather_fetch(data: WeatherFetchRequest):
    # Basic sanity checks (could be improved)
    required_fields = {"latitude", "longitude", "parameters", "start_date", "end_date"}
    if not data or not required_fields.issubset(data.__dict__.keys()):
        return jsonify({"error": "Missing required fields"}), 400

    request_id = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    entity_jobs[request_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
    }
    asyncio.create_task(process_entity(request_id, data.__dict__))
    return jsonify({"request_id": request_id, "status": "processing"}), 202

@app.route("/weather/result/<request_id>", methods=["GET"])
async def weather_result(request_id):
    job = entity_jobs.get(request_id)
    if not job:
        return jsonify({"error": "Request ID not found"}), 404
    status = job.get("status", "processing")
    if status == "processing":
        return jsonify({"request_id": request_id, "status": "processing"}), 200
    elif status == "completed":
        return jsonify({
            "request_id": request_id,
            "status": "completed",
            "data": job.get("data", {})
        }), 200
    elif status == "failed":
        return jsonify({
            "request_id": request_id,
            "status": "failed",
            "error": job.get("error", "Unknown error")
        }), 500
    else:
        return jsonify({"error": "Unknown job status"}), 500

async def fetch_weather_data(latitude: float, longitude: float, parameters: List[str], start_date: str, end_date: str):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(parameters),
        "timezone": "UTC",
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.exception(f"Failed to fetch weather data: {e}")
            raise

async def process_entity(job_id: str, data: dict):
    try:
        raw_data = await fetch_weather_data(
            latitude=data["latitude"],
            longitude=data["longitude"],
            parameters=data["parameters"],
            start_date=data["start_date"],
            end_date=data["end_date"],
        )
        hourly = raw_data.get("hourly", {})
        processed = {"dates": hourly.get("time", [])}
        for param in data["parameters"]:
            processed[param] = hourly.get(param, [])
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["data"] = processed
        entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
        logger.info(f"Job {job_id} completed successfully.")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        logger.exception(f"Job {job_id} failed.")

entity_jobs = {}

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)