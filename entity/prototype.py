```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import httpx
import uuid

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for prototype persistence
# Structure: {data_id: {status:str, requestedAt:str, input:dict, result:dict or None}}
entity_job: Dict[str, Dict[str, Any]] = {}

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


async def fetch_weather_external(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calls the Open-Meteo API with given parameters.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(OPEN_METEO_URL, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.exception(f"HTTP error when calling Open-Meteo API: {e}")
            raise


async def process_entity_job(data_id: str):
    """
    Background task: fetches weather data from external API, stores results in entity_job cache.
    """
    job = entity_job.get(data_id)
    if not job:
        logger.error(f"process_entity_job called for unknown data_id {data_id}")
        return

    job["status"] = "processing"
    input_params = job["input"]

    # Prepare parameters for Open-Meteo API request based on user input
    # Required: latitude, longitude, start_date, end_date, parameters
    latitude = input_params["latitude"]
    longitude = input_params["longitude"]
    start_date = input_params["start_date"]
    end_date = input_params["end_date"]
    parameters = input_params.get("parameters", [])

    # Open-Meteo parameters setup
    # "hourly" parameter should be a comma-separated list of requested parameters
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

        # Simple processing: keep hourly data for requested parameters + timestamps
        hourly_data = external_data.get("hourly", {})
        timestamps = hourly_data.get("time", [])

        # Build filtered parameters dict
        filtered_params = {}
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
        logger.info(f"Weather data fetched and stored for data_id {data_id}")

    except Exception as e:
        job["status"] = "failed"
        job["result"] = None
        logger.exception(f"Failed to fetch weather data for data_id {data_id}: {e}")


@app.route("/weather/fetch", methods=["POST"])
async def fetch_weather():
    """
    POST endpoint to trigger weather data fetch.
    Expects JSON body with latitude, longitude, parameters, start_date, end_date.
    Returns a unique data_id for later retrieval.
    """
    data = await request.get_json(force=True)

    # Basic input validation TODO: extend if needed
    required_fields = ["latitude", "longitude", "start_date", "end_date"]
    for field in required_fields:
        if field not in data:
            return jsonify({"status": "error", "message": f"Missing required field: {field}"}), 400

    parameters = data.get("parameters", [])
    if not isinstance(parameters, list):
        return jsonify({"status": "error", "message": "Field 'parameters' must be a list"}), 400

    data_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()

    # Store initial job info in cache
    entity_job[data_id] = {
        "status": "queued",
        "requestedAt": requested_at,
        "input": data,
        "result": None,
    }

    # Fire and forget background task to fetch and store weather data
    asyncio.create_task(process_entity_job(data_id))

    return jsonify({
        "status": "success",
        "message": "Weather data fetch initiated",
        "data_id": data_id,
    })


@app.route("/weather/result/<data_id>", methods=["GET"])
async def get_weather_result(data_id: str):
    """
    GET endpoint to retrieve stored weather data by data_id.
    """
    job = entity_job.get(data_id)
    if not job:
        return jsonify({"status": "error", "message": "Data ID not found"}), 404

    if job["status"] == "processing" or job["status"] == "queued":
        return jsonify({"status": "processing", "message": "Data is being fetched, please try later."}), 202

    if job["status"] == "failed":
        return jsonify({"status": "failed", "message": "Failed to fetch weather data."}), 500

    # status == completed
    return jsonify(job["result"])


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
