import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache to store latest fetched weather data per location
weather_cache: Dict[str, Dict] = {}

# Placeholder for MSC GeoMet API (use real endpoint/key here)
WEATHERAPI_BASE_URL = "http://api.weatherapi.com/v1/current.json"
WEATHERAPI_KEY = "demo"

@dataclass
class WeatherFetchRequest:
    location: str
    parameters: List[str]
    datetime: Optional[str]

@dataclass
class WeatherResultsQuery:
    location: str

async def fetch_weather_from_external_api(location: str, parameters: List[str], datetime_iso: Optional[str]) -> Dict:
    async with httpx.AsyncClient() as client:
        try:
            params = {"key": WEATHERAPI_KEY, "q": location, "aqi": "no"}
            response = await client.get(WEATHERAPI_BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            current = data.get("current", {})
            result = {}
            if "temperature" in parameters:
                result["temperature"] = current.get("temp_c")
            if "humidity" in parameters:
                result["humidity"] = current.get("humidity")
            if "wind_speed" in parameters:
                result["wind_speed"] = current.get("wind_kph")
            for param in parameters:
                if param not in result:
                    result[param] = None
            return result
        except Exception as e:
            logger.exception(e)
            raise

@app.route("/weather/fetch", methods=["POST"])
@validate_request(WeatherFetchRequest)  # validation last for POST due to quart-schema issue
async def weather_fetch(data: WeatherFetchRequest):
    if not data.location or not isinstance(data.parameters, list):
        return jsonify({"status": "failure", "message": "Invalid 'location' or 'parameters'"}), 400
    asyncio.create_task(process_fetch_job(data.location, data.parameters, data.datetime))
    return jsonify({
        "status": "success",
        "message": "Weather fetch started. Use GET /weather/results to retrieve data.",
        "data": None
    })

async def process_fetch_job(location: str, parameters: List[str], datetime_iso: Optional[str]):
    try:
        fetched_data = await fetch_weather_from_external_api(location, parameters, datetime_iso)
        weather_cache[location] = {
            "timestamp": datetime.utcnow().isoformat(),
            "data": fetched_data
        }
        logger.info(f"Weather data fetched and cached for location: {location}")
    except Exception as e:
        logger.error(f"Error processing weather fetch job for {location}: {e}")

@validate_querystring(WeatherResultsQuery)  # validation first for GET due to quart-schema issue
@app.route("/weather/results", methods=["GET"])
async def weather_results():
    location = request.args.get("location")
    cached = weather_cache.get(location)
    if not cached:
        return jsonify({"message": "No data available for the requested location"}), 404
    return jsonify({
        "location": location,
        "timestamp": cached["timestamp"],
        "data": cached["data"]
    })

if __name__ == "__main__":
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)