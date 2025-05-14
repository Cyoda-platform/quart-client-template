import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Any

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data models for request validation
@dataclass
class WeatherFetchRequest:
    location: str
    data_type: str

@dataclass
class WeatherDataQuery:
    location: str
    data_type: str

# In-memory cache for weather data and jobs
weather_data_cache: Dict[str, Dict[str, Any]] = {}
entity_jobs: Dict[str, Dict[str, Any]] = {}

# Constants / config for MSC GeoMet API
# TODO: Confirm exact MSC GeoMet API endpoint and query parameters
MSC_GEOMET_BASE_URL = "https://opendata-download-metfcst.smhi.se/api/category/pmp3g/version/2/geotype/point/lon/{lon}/lat/{lat}/data.json"

def generate_job_id() -> str:
    return datetime.utcnow().strftime("%Y%m%d%H%M%S%f")

async def fetch_weather_from_mscc_geomet(location: str, data_type: str) -> Dict[str, Any]:
    try:
        lat_lon = location.split(",")
        if len(lat_lon) != 2:
            raise ValueError("Invalid location format. Expected 'lat,lon'")
        lat, lon = lat_lon[0].strip(), lat_lon[1].strip()
        url = MSC_GEOMET_BASE_URL.format(lat=lat, lon=lon)
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        # TODO: Process data further according to data_type
        return data
    except Exception as e:
        logger.exception(e)
        raise

async def process_entity(job_id: str, location: str, data_type: str):
    try:
        entity_jobs[job_id]["status"] = "processing"
        weather = await fetch_weather_from_mscc_geomet(location, data_type)
        cache_key = f"{location}|{data_type}"
        weather_data_cache[cache_key] = {
            "location": location,
            "data_type": data_type,
            "data": weather,
            "updatedAt": datetime.utcnow().isoformat() + "Z"
        }
        entity_jobs[job_id]["status"] = "done"
        entity_jobs[job_id]["result_key"] = cache_key
    except Exception:
        entity_jobs[job_id]["status"] = "failed"

@app.route("/weather/fetch", methods=["POST"])
@validate_request(WeatherFetchRequest)  # validation last for POST due to quart-schema defect workaround
async def weather_fetch(data: WeatherFetchRequest):
    job_id = generate_job_id()
    entity_jobs[job_id] = {
        "status": "queued",
        "requestedAt": datetime.utcnow().isoformat() + "Z"
    }
    asyncio.create_task(process_entity(job_id, data.location, data.data_type))
    return jsonify({
        "status": "success",
        "message": "Weather data fetch started",
        "job_id": job_id
    })

@validate_querystring(WeatherDataQuery)  # validation first for GET due to quart-schema defect workaround
@app.route("/weather/data", methods=["GET"])
async def weather_data():
    location = request.args.get("location")
    data_type = request.args.get("data_type")
    cache_key = f"{location}|{data_type}"
    data = weather_data_cache.get(cache_key)
    if not data:
        return jsonify({"status": "error", "message": "No data found"}), 404
    return jsonify(data)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)