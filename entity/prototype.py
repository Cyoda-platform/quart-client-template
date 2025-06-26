```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory async-safe cache for storing job results
entity_jobs: Dict[str, Dict[str, Any]] = {}
jobs_lock = asyncio.Lock()


async def fetch_weather_from_api(latitude: float, longitude: float, parameters: list, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
    """
    Calls the real external weather API (https://api.open-meteo.com/v1/forecast) and returns data.
    """
    base_url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(parameters)
    }
    # Add optional date filters if provided
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
    """
    Background task to fetch weather data from the external API and update the job status & data.
    """
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
async def weather_fetch():
    data = await request.get_json()
    # Basic validation (since no @validate_request)
    required_fields = ["latitude", "longitude", "parameters"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # Generate a UUID for the job id
    import uuid

    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat() + "Z"

    job_entry = {
        "status": "processing",
        "requestedAt": requested_at,
    }

    async with jobs_lock:
        entity_jobs[job_id] = job_entry

    # Fire and forget the processing task
    asyncio.create_task(process_entity(job_id, data))

    return jsonify({"request_id": job_id, "status": "processing"}), 202


@app.route("/weather/result/<string:request_id>", methods=["GET"])
async def weather_result(request_id):
    async with jobs_lock:
        job = entity_jobs.get(request_id)

    if not job:
        return jsonify({"error": "Request ID not found"}), 404

    # Compose response according to spec
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
```
