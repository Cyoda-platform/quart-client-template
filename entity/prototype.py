from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data model for request validation
@dataclass
class WeatherFetchRequest:
    latitude: float
    longitude: float
    parameters: List[str]
    start_date: Optional[str] = None
    end_date: Optional[str] = None

# In-memory async-safe cache for storing job results
entity_jobs: Dict[str, Dict[str, Any]] = {}
jobs_lock = asyncio.Lock()

async def fetch_weather_from_api(latitude: float, longitude: float, parameters: list, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
    base_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(parameters)
    }
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(base_url, params=params)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.exception(f"Error fetching weather data from external API: {e}")
            raise

async def process_entity(job_id: str, data: dict):
    try:
        weather_data = await fetch_weather_from_api(
            latitude=data["latitude"],
            longitude=data["longitude"],
            parameters=data["parameters"],
            start_date=data.get("start_date"),
            end_date=data.get("end_date")
        )
        async with jobs_lock:
            entity_jobs[job_id]["status"] = "completed"
            entity_jobs[job_id]["data"] = weather_data
            entity_jobs[job_id]["parameters"] = data["parameters"]
            entity_jobs[job_id]["location"] = {"latitude": data["latitude"], "longitude": data["longitude"]}
            entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat() + "Z"
    except Exception as e:
        async with jobs_lock:
            entity_jobs[job_id]["status"] = "failed"
            entity_jobs[job_id]["error"] = str(e)
            entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat() + "Z"
        logger.exception(f"Failed processing job {job_id}")

@app.route("/weather/fetch", methods=["POST"])
# Workaround for quart-schema defect: place validate_request after route for POST
@validate_request(WeatherFetchRequest)
async def weather_fetch(data: WeatherFetchRequest):
    job_id = __import__("uuid").uuid4().hex
    requested_at = datetime.utcnow().isoformat() + "Z"
    async with jobs_lock:
        entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}

    # Fire and forget background processing
    asyncio.create_task(process_entity(job_id, data.__dict__))
    return jsonify({"request_id": job_id, "status": "processing"}), 202

@app.route("/weather/result/<string:request_id>", methods=["GET"])
async def weather_result(request_id):
    async with jobs_lock:
        job = entity_jobs.get(request_id)

    if not job:
        return jsonify({"error": "Request ID not found"}), 404

    response = {
        "request_id": request_id,
        "status": job.get("status"),
        "requestedAt": job.get("requestedAt"),
    }
    if job["status"] == "completed":
        response.update({
            "location": job.get("location"),
            "parameters": job.get("parameters"),
            "data": job.get("data"),
            "completedAt": job.get("completedAt"),
        })
    elif job["status"] == "failed":
        response.update({
            "error": job.get("error"),
            "completedAt": job.get("completedAt"),
        })

    return jsonify(response)

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)