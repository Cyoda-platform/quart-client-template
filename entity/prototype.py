```python
import asyncio
import logging
from datetime import datetime
import uuid

from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for fetch jobs and results
entity_job = {}

MSC_GEOMET_BASE_URL = "https://api.meteo.lt/v1"  # Example real MSC GeoMet API base URL
# TODO: Adjust MSC_GEOMET_BASE_URL and endpoints if official docs specify different URLs.

async def fetch_weather_from_msgeomet(location: str, parameters: list, date: str = None):
    """Fetch weather data from MSC GeoMet public API."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # For demo purpose, assume 'location' is a city name and date is ignored (current weather)
            # MSC GeoMet API example: /places/{location}/forecasts/long-term
            # We'll fetch current weather for location:
            url = f"{MSC_GEOMET_BASE_URL}/places/{location}/forecasts/long-term"
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            # TODO: Map and filter data according to requested parameters and date
            # For simplicity, we pick the first forecast day and extract parameters if present

            # This is a simplified example extracting some values from the response
            forecasts = data.get("forecastTimestamps", [])
            if not forecasts:
                return {}

            forecast = forecasts[0]  # Pick the earliest forecast available

            extracted = {}
            if "temperature" in parameters and "airTemperature" in forecast:
                extracted["temperature"] = forecast["airTemperature"]
            if "humidity" in parameters and "relativeHumidity" in forecast:
                extracted["humidity"] = forecast["relativeHumidity"]
            if "wind_speed" in parameters and "windSpeed" in forecast:
                extracted["wind_speed"] = forecast["windSpeed"]
            return extracted

        except Exception as e:
            logger.exception(f"Error fetching weather from MSC GeoMet: {e}")
            return None


async def process_entity(job_id: str, location: str, parameters: list, date: str):
    """Background task processing the weather fetch job."""
    try:
        entity_job[job_id]["status"] = "processing"
        data = await fetch_weather_from_msgeomet(location, parameters, date)
        if data is None:
            entity_job[job_id]["status"] = "error"
            entity_job[job_id]["result"] = {}
        else:
            entity_job[job_id]["status"] = "completed"
            entity_job[job_id]["result"] = {
                "location": location,
                "parameters": data,
                "date": date if date else datetime.utcnow().strftime("%Y-%m-%d"),
                "retrieved_at": datetime.utcnow().isoformat() + "Z",
            }
    except Exception as e:
        logger.exception(e)
        entity_job[job_id]["status"] = "error"
        entity_job[job_id]["result"] = {}


@app.route("/weather/fetch", methods=["POST"])
async def fetch_weather():
    body = await request.get_json()
    location = body.get("location")
    parameters = body.get("parameters", [])
    date = body.get("date")  # optional

    if not location or not isinstance(parameters, list) or not parameters:
        return jsonify({"status": "error", "message": "Missing or invalid 'location' or 'parameters'"}), 400

    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat() + "Z"
    entity_job[job_id] = {"status": "queued", "requestedAt": requested_at}

    # Fire and forget background processing
    asyncio.create_task(process_entity(job_id, location, parameters, date))

    return jsonify({
        "status": "success",
        "fetch_id": job_id,
        "message": "Data fetching started"
    })


@app.route("/weather/result/<fetch_id>", methods=["GET"])
async def get_result(fetch_id):
    job = entity_job.get(fetch_id)
    if not job:
        return jsonify({"status": "error", "message": "fetch_id not found"}), 404

    if job["status"] == "processing" or job["status"] == "queued":
        return jsonify({"status": "processing", "message": "Result not ready yet"}), 202

    if job["status"] == "error":
        return jsonify({"status": "error", "message": "Failed to fetch data"}), 500

    return jsonify({
        "fetch_id": fetch_id,
        **job["result"],
    })


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
