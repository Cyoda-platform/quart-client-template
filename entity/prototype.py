from dataclasses import dataclass
from typing import List
import asyncio
import logging
from datetime import datetime
from uuid import uuid4

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data model for POST /weather/fetch
@dataclass
class WeatherFetch:
    latitude: float
    longitude: float
    parameters: List[str]
    start_date: str
    end_date: str

# In-memory async-safe cache for prototype persistence
entity_jobs = {}

async def fetch_weather_data(latitude, longitude, parameters, start_date, end_date):
    base_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "timezone": "UTC",
        "hourly": ",".join(parameters),
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(base_url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.exception(f"HTTP error fetching weather data: {e}")
            raise

async def process_entity(entity_store, job_id, data):
    try:
        entity_store[job_id]["status"] = "fetching"
        weather_data = await fetch_weather_data(
            data["latitude"],
            data["longitude"],
            data["parameters"],
            data["start_date"],
            data["end_date"],
        )
        # TODO: add any data transformations if needed
        entity_store[job_id]["status"] = "completed"
        entity_store[job_id]["result"] = {
            "request_id": job_id,
            "latitude": data["latitude"],
            "longitude": data["longitude"],
            "parameters": weather_data.get("hourly", {}),
            "start_date": data["start_date"],
            "end_date": data["end_date"],
            "fetched_at": datetime.utcnow().isoformat() + "Z",
        }
        logger.info(f"Weather data fetch completed for job_id: {job_id}")
    except Exception as e:
        entity_store[job_id]["status"] = "failed"
        entity_store[job_id]["error"] = str(e)
        logger.exception(f"Failed to process entity for job_id {job_id}")

@app.route("/weather/fetch", methods=["POST"])
# Workaround: validate_request must come after @app.route for POST due to quart-schema defect
@validate_request(WeatherFetch)
async def weather_fetch(data: WeatherFetch):
    job_id = str(uuid4())
    requested_at = datetime.utcnow().isoformat() + "Z"
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": requested_at,
    }
    # Fire-and-forget processing
    asyncio.create_task(process_entity(entity_jobs, job_id, data.__dict__))
    return jsonify({
        "status": "success",
        "message": "Weather data fetch initiated",
        "request_id": job_id,
    })

@app.route("/weather/result/<job_id>", methods=["GET"])
async def weather_result(job_id):
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"status": "error", "message": "Request ID not found"}), 404
    if job["status"] in ("processing", "fetching"):
        return jsonify({"status": "processing", "message": "Data is still being fetched"}), 202
    if job["status"] == "failed":
        return jsonify({"status": "failed", "error": job.get("error", "Unknown error")}), 500
    return jsonify({"status": "success", "data": job.get("result")})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)