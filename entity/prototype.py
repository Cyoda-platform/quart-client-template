import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Tuple

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Request schemas
@dataclass
class FetchRequest:
    locations: list  # List of {"latitude": float, "longitude": float}

@dataclass
class WeatherQuery:
    lat: float
    lon: float

# In-memory cache for weather data keyed by (lat, lon)
weather_cache: Dict[Tuple[float, float], Dict] = {}
entity_job = {}

MSC_GEOMET_BASE_URL = "https://api.msc-geomet.com/weather"  # TODO: replace with actual URL

async def fetch_weather_for_location(client: httpx.AsyncClient, lat: float, lon: float) -> Dict:
    try:
        params = {"lat": lat, "lon": lon}
        response = await client.get(MSC_GEOMET_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
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
                    logger.warning(f"Skipping location with missing data: {loc}")
                    continue
                try:
                    data = await fetch_weather_for_location(client, lat, lon)
                    weather_cache[(lat, lon)] = {
                        "data": data,
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }
                    logger.info(f"Cached data for ({lat}, {lon})")
                except Exception:
                    pass
        entity_job[job_id]["status"] = "done"
    except Exception as e:
        entity_job[job_id]["status"] = "failed"
        logger.exception(f"Job {job_id} failed: {e}")

@app.route("/weather/fetch", methods=["POST"])
# workaround: validate_request must be last for POST due to library defect
@validate_request(FetchRequest)
async def weather_fetch(data: FetchRequest):
    locations = data.locations
    if not isinstance(locations, list) or not locations:
        return jsonify({"status": "error", "message": "No locations provided"}), 400

    job_id = f"job_{datetime.utcnow().timestamp()}"
    entity_job[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat() + "Z"}
    asyncio.create_task(process_fetch_job(job_id, locations))

    return jsonify({
        "status": "success",
        "message": "Weather data fetching initiated",
        "requested_locations": len(locations)
    })

# workaround: validate_querystring must be first for GET due to library defect
@validate_querystring(WeatherQuery)
@app.route("/weather/results", methods=["GET"])
async def weather_results():
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

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)