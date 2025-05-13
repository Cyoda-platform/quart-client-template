from dataclasses import dataclass
from typing import List, Dict, Any
import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data models for request validation
@dataclass
class Location:
    city: str
    country: str

@dataclass
class FetchRequest:
    locations: List[Location]

# In-memory cache for weather data keyed by "city,country"
weather_cache: Dict[str, Dict[str, Any]] = {}

# In-memory job status store keyed by job_id
entity_job: Dict[str, Dict[str, Any]] = {}

# Base URL for MSC GeoMet public API (TODO: replace with real endpoint)
MSC_GEOMET_BASE_URL = "https://api.msc-geomet.example.com/weather"  # TODO

async def fetch_weather_for_location(client: httpx.AsyncClient, city: str, country: str) -> Dict[str, Any]:
    try:
        params = {"city": city, "country": country}
        resp = await client.get(MSC_GEOMET_BASE_URL, params=params, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        # TODO: adjust parsing to real API response
        return {
            "temperature": data.get("temperature"),
            "humidity": data.get("humidity"),
            "conditions": data.get("conditions", "unknown"),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        logger.exception(f"Failed to fetch weather for {city}, {country}: {e}")
        return {
            "temperature": None,
            "humidity": None,
            "conditions": "error",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

async def process_entity(job_id: str, locations: List[Location]):
    async with httpx.AsyncClient() as client:
        for loc in locations:
            weather = await fetch_weather_for_location(client, loc.city, loc.country)
            key = f"{loc.city.lower()},{loc.country.lower()}"
            weather_cache[key] = {
                "location": {"city": loc.city, "country": loc.country},
                "weatherData": weather,
            }
    entity_job[job_id]["status"] = "completed"
    entity_job[job_id]["completedAt"] = datetime.utcnow().isoformat() + "Z"
    logger.info(f"Completed job {job_id}")

@app.route("/weather/fetch", methods=["POST"])
# workaround: validate_request must be last decorator on POST due to quart-schema defect
@validate_request(FetchRequest)
async def fetch_weather(data: FetchRequest):
    try:
        locations = data.locations
        if not locations:
            return jsonify({"status": "error", "message": "locations must be a non-empty list"}), 400
        job_id = datetime.utcnow().isoformat() + "-" + str(id(locations))
        entity_job[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat() + "Z"}
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