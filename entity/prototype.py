```python
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache to mock persistence: weather_id -> weather data
weather_cache = {}

# TODO: Replace with your actual OpenWeatherMap API key
OPENWEATHER_API_KEY = "your_openweathermap_api_key"
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"


async def fetch_current_weather(location):
    """
    Calls OpenWeatherMap current weather data API.
    Location can be city name or lat/lon.
    """
    params = {"appid": OPENWEATHER_API_KEY, "units": "metric"}

    if location.get("city"):
        params["q"] = location["city"]
    elif location.get("latitude") is not None and location.get("longitude") is not None:
        params["lat"] = location["latitude"]
        params["lon"] = location["longitude"]
    else:
        raise ValueError("Location must have either city or latitude & longitude")

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{OPENWEATHER_BASE_URL}/weather", params=params)
        resp.raise_for_status()
        return resp.json()


async def fetch_forecast_weather(location):
    """
    Calls OpenWeatherMap forecast API (5 day / 3 hour forecast).
    Location can be city name or lat/lon.
    """
    params = {"appid": OPENWEATHER_API_KEY, "units": "metric"}

    if location.get("city"):
        params["q"] = location["city"]
    elif location.get("latitude") is not None and location.get("longitude") is not None:
        params["lat"] = location["latitude"]
        params["lon"] = location["longitude"]
    else:
        raise ValueError("Location must have either city or latitude & longitude")

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{OPENWEATHER_BASE_URL}/forecast", params=params)
        resp.raise_for_status()
        return resp.json()


async def process_weather_fetch(job_id, payload):
    """
    Fire-and-forget background task to call external API, store result in cache.
    """
    try:
        location = payload.get("location", {})
        data_type = payload.get("data_type", "current")

        if data_type == "current":
            weather_data = await fetch_current_weather(location)
        elif data_type == "forecast":
            weather_data = await fetch_forecast_weather(location)
        else:
            raise ValueError(f"Unsupported data_type: {data_type}")

        # Prepare stored record
        record = {
            "weather_id": job_id,
            "location": location,
            "data_type": data_type,
            "weather_data": weather_data,
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "status": "completed",
        }

        weather_cache[job_id] = record
        logger.info(f"Weather data stored for job_id={job_id}")

    except Exception as e:
        logger.exception(e)
        weather_cache[job_id] = {
            "status": "failed",
            "error": str(e),
            "fetched_at": datetime.utcnow().isoformat() + "Z",
        }


@app.route("/weather/fetch", methods=["POST"])
async def weather_fetch():
    """
    POST endpoint to trigger weather data fetch.
    """
    try:
        payload = await request.get_json()

        # Validate minimal presence of parameters
        if not payload or "location" not in payload or "data_type" not in payload:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Missing required fields: location and data_type",
                    }
                ),
                400,
            )

        job_id = str(uuid.uuid4())
        weather_cache[job_id] = {
            "status": "processing",
            "requestedAt": datetime.utcnow().isoformat() + "Z",
        }

        # Fire and forget background processing
        asyncio.create_task(process_weather_fetch(job_id, payload))

        return jsonify(
            {
                "status": "success",
                "weather_id": job_id,
                "message": "Data fetch started successfully",
            }
        )

    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/weather/<weather_id>", methods=["GET"])
async def weather_get(weather_id):
    """
    GET endpoint to retrieve stored weather data by id.
    """
    record = weather_cache.get(weather_id)
    if not record:
        return jsonify({"status": "error", "message": "weather_id not found"}), 404

    # If still processing, return status
    if record.get("status") == "processing":
        return jsonify(
            {
                "weather_id": weather_id,
                "status": "processing",
                "message": "Data is still being fetched, please try again later",
            }
        ), 202

    # If failed
    if record.get("status") == "failed":
        return jsonify(
            {
                "weather_id": weather_id,
                "status": "failed",
                "error": record.get("error", "Unknown error"),
            }
        ), 500

    # Success: return full stored record except internal status field
    response = {
        "weather_id": record["weather_id"],
        "location": record["location"],
        "data_type": record["data_type"],
        "weather_data": record["weather_data"],
        "fetched_at": record["fetched_at"],
    }
    return jsonify(response)


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
