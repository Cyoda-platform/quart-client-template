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

# In-memory async-safe cache for storing fetched weather data
# Key: dataId (str), Value: dict with weather data and metadata
entity_job: Dict[str, Dict[str, Any]] = {}
entity_job_lock = asyncio.Lock()


async def process_entity(data_id: str, latitude: float, longitude: float, parameters: list):
    """
    Fetch weather data from open-meteo.com asynchronously,
    store it in the in-memory cache with dataId as key.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current_weather": "true",  # to get current weather snapshot
        # open-meteo API expects parameters under "hourly" or "daily"
        # We'll request hourly and filter only requested parameters.
        "hourly": ",".join(parameters),
        "timezone": "UTC",
    }

    logger.info(f"Fetching weather data from external API for dataId={data_id}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            weather_data = response.json()

        # TODO: If needed, process or filter weather_data more precisely here.

        async with entity_job_lock:
            entity_job[data_id].update({
                "status": "completed",
                "data": weather_data,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "latitude": latitude,
                "longitude": longitude,
                "parameters": parameters,
            })
        logger.info(f"Weather data stored successfully for dataId={data_id}")

    except Exception as e:
        logger.exception(f"Failed to fetch weather data for dataId={data_id}: {e}")
        async with entity_job_lock:
            entity_job[data_id].update({
                "status": "failed",
                "error": str(e)
            })


@app.route("/weather/fetch", methods=["POST"])
async def fetch_weather():
    """
    POST /weather/fetch
    Request JSON:
    {
        "latitude": float,
        "longitude": float,
        "parameters": [str, ...]
    }
    Response JSON:
    {
        "status": "success" | "error",
        "message": str,
        "dataId": str (if success)
    }
    """
    data = await request.get_json()
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    parameters = data.get("parameters", [])

    # Basic input validation
    if not (isinstance(latitude, (int, float)) and isinstance(longitude, (int, float))):
        return jsonify({"status": "error", "message": "Invalid or missing latitude/longitude"}), 400
    if not (isinstance(parameters, list) and all(isinstance(p, str) for p in parameters)):
        return jsonify({"status": "error", "message": "Invalid or missing parameters list"}), 400

    # Generate unique dataId (simple timestamp-based)
    data_id = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")

    async with entity_job_lock:
        entity_job[data_id] = {
            "status": "processing",
            "requestedAt": datetime.utcnow().isoformat() + "Z"
        }

    # Fire and forget the processing task
    asyncio.create_task(process_entity(data_id, latitude, longitude, parameters))

    return jsonify({
        "status": "success",
        "message": "Weather data fetching started",
        "dataId": data_id
    })


@app.route("/weather/result/<data_id>", methods=["GET"])
async def get_weather_result(data_id):
    """
    GET /weather/result/{dataId}
    Returns stored weather data or current status.
    """
    async with entity_job_lock:
        entry = entity_job.get(data_id)

    if not entry:
        return jsonify({"status": "error", "message": "dataId not found"}), 404

    if entry["status"] == "processing":
        return jsonify({"status": "processing", "message": "Data is still being fetched"}), 202

    if entry["status"] == "failed":
        return jsonify({"status": "error", "message": entry.get("error", "Unknown error")}), 500

    # Compose response with stored data
    response = {
        "dataId": data_id,
        "latitude": entry.get("latitude"),
        "longitude": entry.get("longitude"),
        "parameters": {},  # to be populated below
        "timestamp": entry.get("timestamp"),
    }

    # Extract requested parameters from the API response
    data = entry.get("data", {})
    hourly = data.get("hourly", {})
    for param in entry.get("parameters", []):
        values = hourly.get(param)
        if values:
            # Provide latest value as example
            response["parameters"][param] = values[-1] if isinstance(values, list) else values
        else:
            response["parameters"][param] = None  # Not found in response

    return jsonify(response)


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```