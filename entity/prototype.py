```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for weather data keyed by "city,country"
weather_cache: Dict[str, Dict[str, Any]] = {}

# In-memory job status store keyed by job_id (UUID as string)
entity_job: Dict[str, Dict[str, Any]] = {}

# Base URL for MSC GeoMet public API (TODO: Confirm actual endpoint and parameters)
MSC_GEOMET_BASE_URL = "https://api.msc-geomet.example.com/weather"  # <-- TODO: Replace with real GeoMet API endpoint


async def fetch_weather_for_location(client: httpx.AsyncClient, city: str, country: str) -> Dict[str, Any]:
    """
    Fetch weather data from MSC GeoMet API for given city and country.

    TODO: Adjust parameters and response parsing per real API spec.
    """
    try:
        # Example query params - adapt to real API
        params = {"city": city, "country": country}
        resp = await client.get(MSC_GEOMET_BASE_URL, params=params, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()

        # TODO: Adjust parsing according to actual API response
        weather_data = {
            "temperature": data.get("temperature"),
            "humidity": data.get("humidity"),
            "conditions": data.get("conditions", "unknown"),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        return weather_data

    except Exception as e:
        logger.exception(f"Failed to fetch weather for {city}, {country}: {e}")
        # Return minimal fallback info
        return {
            "temperature": None,
            "humidity": None,
            "conditions": "error",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }


async def process_entity(job_id: str, locations: list):
    """
    Background task to fetch weather for all requested locations,
    update cache and job status.
    """
    async with httpx.AsyncClient() as client:
        for loc in locations:
            city = loc.get("city")
            country = loc.get("country")
            if not city or not country:
                logger.warning(f"Skipping invalid location entry: {loc}")
                continue

            weather = await fetch_weather_for_location(client, city, country)
            key = f"{city.lower()},{country.lower()}"
            weather_cache[key] = {
                "location": {"city": city, "country": country},
                "weatherData": weather,
            }

    entity_job[job_id]["status"] = "completed"
    entity_job[job_id]["completedAt"] = datetime.utcnow().isoformat() + "Z"
    logger.info(f"Completed job {job_id}")


@app.route("/weather/fetch", methods=["POST"])
async def fetch_weather():
    """
    POST /weather/fetch
    Request JSON: { locations: [ { city: str, country: str }, ... ] }
    Response JSON: { status: "success", message: str, fetchedAt: timestamp }
    """
    try:
        data = await request.get_json()
        locations = data.get("locations", [])
        if not isinstance(locations, list) or not locations:
            return jsonify({"status": "error", "message": "locations must be a non-empty list"}), 400

        job_id = datetime.utcnow().isoformat() + "-" + str(id(locations))  # Simple job id - TODO: Use UUID if needed
        entity_job[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat() + "Z"}

        # Fire and forget the processing task
        asyncio.create_task(process_entity(job_id, locations))

        return jsonify({
            "status": "success",
            "message": "Weather data fetch initiated",
            "fetchedAt": datetime.utcnow().isoformat() + "Z",
            "jobId": job_id
        })

    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@app.route("/weather/<string:location>", methods=["GET"])
async def get_weather(location):
    """
    GET /weather/{location}
    location format: city,country (case-insensitive)

    Response JSON: {
        location: { city, country },
        weatherData: { temperature, humidity, conditions, timestamp }
    }
    """
    try:
        key = location.lower()
        data = weather_cache.get(key)
        if not data:
            return jsonify({"status": "error", "message": f"No weather data found for {location}"}), 404

        return jsonify(data)

    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
