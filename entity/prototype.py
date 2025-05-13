```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, List

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache to store latest fetched weather data per location
# Structure: {location: {"timestamp": datetime, "data": {...}}}
weather_cache: Dict[str, Dict] = {}

# TODO: Replace with MSC GeoMet actual API endpoint and key if required
MSC_GEOMET_API_URL = "https://api.meteo.fr/v1/forecast"  # Placeholder URL
# Note: Since MSC GeoMet API docs are not provided here, will use a public weather API that resembles expected usage.
# For demo, let's use https://api.weatherapi.com/v1/current.json?key=YOUR_KEY&q=LOCATION
# We'll use WeatherAPI as a stand-in for MSC GeoMet here.
WEATHERAPI_BASE_URL = "http://api.weatherapi.com/v1/current.json"
WEATHERAPI_KEY = "demo"  # demo key with limited access, replace with real key


async def fetch_weather_from_external_api(location: str, parameters: List[str], datetime_iso: Optional[str]) -> Dict:
    """
    Fetch weather data from external API (using WeatherAPI.com here as a stand-in for MSC GeoMet).
    Supports current weather only (datetime_iso ignored - TODO: support historical if MSC GeoMet supports).
    """
    async with httpx.AsyncClient() as client:
        try:
            # MSC GeoMet or other API integration should happen here.
            # TODO: Adjust request to MSC GeoMet API once endpoint and params known.
            # Here, we ignore datetime_iso because WeatherAPI free tier supports only current weather.
            params = {
                "key": WEATHERAPI_KEY,
                "q": location,
                "aqi": "no",
            }
            response = await client.get(WEATHERAPI_BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            current = data.get("current", {})

            result = {}
            if "temperature" in parameters:
                # WeatherAPI returns temp_c
                result["temperature"] = current.get("temp_c")
            if "humidity" in parameters:
                result["humidity"] = current.get("humidity")
            if "wind_speed" in parameters:
                result["wind_speed"] = current.get("wind_kph")  # converted kph, approx to wind speed

            # Add any requested parameters but not available - set None
            for param in parameters:
                if param not in result:
                    result[param] = None

            return result

        except httpx.HTTPError as e:
            logger.exception(f"HTTP error while fetching weather data: {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error while fetching weather data: {e}")
            raise


@app.route("/weather/fetch", methods=["POST"])
async def weather_fetch():
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"status": "failure", "message": "Invalid or missing JSON body"}), 400

        location = data.get("location")
        parameters = data.get("parameters", [])
        datetime_iso = data.get("datetime")  # optional

        if not location or not isinstance(parameters, list):
            return (
                jsonify(
                    {
                        "status": "failure",
                        "message": "Missing or invalid 'location' or 'parameters' fields",
                    }
                ),
                400,
            )

        # Start processing task asynchronously (fire and forget)
        job_id = location + "_" + datetime.utcnow().isoformat()

        # Mark job as processing (not stored or used further here, just demo)
        # We could extend for job status tracking if needed.
        asyncio.create_task(process_fetch_job(location, parameters, datetime_iso))

        return jsonify(
            {
                "status": "success",
                "message": "Weather fetch started. Use GET /weather/results to retrieve data.",
                "data": None,
            }
        )

    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "failure", "message": "Internal server error"}), 500


async def process_fetch_job(location: str, parameters: List[str], datetime_iso: Optional[str]):
    try:
        fetched_data = await fetch_weather_from_external_api(location, parameters, datetime_iso)
        weather_cache[location] = {
            "timestamp": datetime.utcnow().isoformat(),
            "data": fetched_data,
        }
        logger.info(f"Weather data fetched and cached for location: {location}")
    except Exception as e:
        logger.error(f"Error processing weather fetch job for {location}: {e}")


@app.route("/weather/results", methods=["GET"])
async def weather_results():
    try:
        location = request.args.get("location")
        if not location:
            return jsonify({"message": "Missing required query parameter 'location'"}), 400

        cached = weather_cache.get(location)
        if not cached:
            return jsonify({"message": "No data available for the requested location"}), 404

        return jsonify(
            {
                "location": location,
                "timestamp": cached["timestamp"],
                "data": cached["data"],
            }
        )

    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal server error"}), 500


if __name__ == "__main__":
    import sys
    import logging

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
