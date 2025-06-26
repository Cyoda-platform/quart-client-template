```python
import asyncio
import logging
from datetime import datetime
from typing import Dict

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

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


async def process_entity(job_id: str, data: dict):
    try:
        latitude = data["latitude"]
        longitude = data["longitude"]
        parameters = data["parameters"]
        start_date = data["start_date"]
        end_date = data["end_date"]

        raw_weather = await fetch_weather_data(latitude, longitude, parameters, start_date, end_date)

        # TODO: Add any additional processing/filtering here if needed
        # For prototype, just store hourly data for requested parameters

        hourly_data = raw_weather.get("hourly", {})
        filtered_data = {param: hourly_data.get(param, []) for param in parameters}

        entity_job[job_id].update(
            {
                "status": "completed",
                "result": {
                    "request_id": job_id,
                    "latitude": latitude,
                    "longitude": longitude,
                    "data": filtered_data,
                    "date_range": {"start": start_date, "end": end_date},
                },
                "completedAt": datetime.utcnow().isoformat() + "Z",
            }
        )
        logger.info(f"Job {job_id} completed successfully")
    except Exception as e:
        entity_job[job_id].update({"status": "failed", "error": str(e)})
        logger.exception(f"Job {job_id} failed")


@app.route("/weather/fetch", methods=["POST"])
async def weather_fetch():
    try:
        data = await request.get_json()
        # Basic input keys validation (not full schema validation)
        required_keys = {"latitude", "longitude", "parameters", "start_date", "end_date"}
        if not data or not required_keys.issubset(data.keys()):
            return jsonify({"status": "error", "message": "Missing required fields"}), 400

        # Generate a simple unique job/request id
        request_id = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")

        # Initialize job state
        entity_job[request_id] = {
            "status": "processing",
            "requestedAt": datetime.utcnow().isoformat() + "Z",
        }

        # Fire and forget processing task
        asyncio.create_task(process_entity(request_id, data))

        return jsonify(
            {
                "status": "success",
                "message": "Weather data fetch initiated",
                "request_id": request_id,
            }
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@app.route("/weather/result/<request_id>", methods=["GET"])
async def weather_result(request_id: str):
    job = entity_job.get(request_id)
    if not job:
        return jsonify({"status": "error", "message": "Request ID not found"}), 404

    if job["status"] == "processing":
        return jsonify({"status": "processing", "message": "Data is still being fetched"}), 202

    if job["status"] == "failed":
        return jsonify({"status": "failed", "message": job.get("error", "Unknown error")}), 500

    # status == completed
    return jsonify(job["result"])


if __name__ == "__main__":
    import sys

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
