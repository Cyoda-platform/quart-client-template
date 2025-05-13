```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Tuple

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for weather data keyed by (lat, lon)
# Structure: {(lat, lon): {"data": {...}, "timestamp": datetime}}
weather_cache: Dict[Tuple[float, float], Dict] = {}

# In-memory job tracking for fetch requests
# Structure: {job_id: {"status": "processing"|"done"|"failed", "requestedAt": datetime}}
entity_job = {}

MSC_GEOMET_BASE_URL = "https://api.msc-geomet.com/weather"  # TODO: Replace with actual MSC GeoMet API base URL
# NOTE: The above URL is a placeholder. Please update with the real MSC GeoMet API endpoint if known.

# TODO: If MSC GeoMet API requires API keys/auth, add here.
# For now, assuming open public API.

async def fetch_weather_for_location(client: httpx.AsyncClient, lat: float, lon: float) -> Dict:
    """
    Fetch weather data from MSC GeoMet API for given lat/lon.
    Returns the JSON response as a dict.

    TODO: Adjust request parameters and URL according to actual MSC GeoMet API spec.
    """
    try:
        # Example: GET request with lat/lon as query parameters
        # If MSC GeoMet has a different call, replace accordingly
        params = {"lat": lat, "lon": lon}
        response = await client.get(MSC_GEOMET_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        logger.exception(f"Failed to fetch weather for ({lat}, {lon}): {e}")
        raise


async def process_fetch_job(job_id: str, locations: list):
    try:
        logger.info(f"Starting processing job {job_id} for locations: {locations}")
        async with httpx.AsyncClient() as client:
            for loc in locations:
                lat = loc.get("latitude")
                lon = loc.get("longitude")
                if lat is None or lon is None:
                    logger.warning(f"Skipping location with missing lat/lon: {loc}")
                    continue
                try:
                    weather_data = await fetch_weather_for_location(client, lat, lon)
                    # Cache the fetched data with timestamp
                    weather_cache[(lat, lon)] = {
                        "data": weather_data,
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }
                    logger.info(f"Cached weather data for ({lat}, {lon})")
                except Exception:
                    # Continue with other locations even if one fails
                    pass
        entity_job[job_id]["status"] = "done"
        logger.info(f"Job {job_id} completed successfully")
    except Exception as e:
        entity_job[job_id]["status"] = "failed"
        logger.exception(f"Job {job_id} failed: {e}")


@app.route("/weather/fetch", methods=["POST"])
async def weather_fetch():
    """
    POST /weather/fetch
    Body JSON:
    {
      "locations": [
        {"latitude": float, "longitude": float},
        ...
      ]
    }
    Response:
    {
      "status": "success",
      "message": "Weather data fetching initiated",
      "requested_locations": int
    }
    """
    data = await request.get_json(force=True)
    locations = data.get("locations", [])
    if not isinstance(locations, list) or not locations:
        return jsonify({"status": "error", "message": "No locations provided"}), 400

    job_id = f"job_{datetime.utcnow().timestamp()}"
    entity_job[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat() + "Z"}

    # Fire and forget the processing task
    asyncio.create_task(process_fetch_job(job_id, locations))

    return jsonify({
        "status": "success",
        "message": "Weather data fetching initiated",
        "requested_locations": len(locations)
    })


@app.route("/weather/results", methods=["GET"])
async def weather_results():
    """
    GET /weather/results?lat=<float>&lon=<float>
    Response:
    {
      "location": {"latitude": float, "longitude": float},
      "weather": {...},
      "timestamp": ISO8601 string
    }
    """
    try:
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)
        if lat is None or lon is None:
            return jsonify({"status": "error", "message": "lat and lon query parameters required"}), 400

        key = (lat, lon)
        cached = weather_cache.get(key)
        if not cached:
            return jsonify({"status": "error", "message": "No weather data found for the requested location"}), 404

        return jsonify({
            "location": {"latitude": lat, "longitude": lon},
            "weather": cached["data"],
            "timestamp": cached["timestamp"]
        })

    except Exception as e:
        logger.exception(f"Error in /weather/results: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
