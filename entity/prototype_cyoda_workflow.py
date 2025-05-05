from dataclasses import dataclass
from typing import Optional

import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@dataclass
class Location:
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

@dataclass
class FetchWeatherRequest:
    location: Location
    data_type: str  # "current", "forecast", or "historical"

def build_openweather_url(location: Location, data_type: str):
    params = {"appid": "YOUR_OPENWEATHERMAP_API_KEY", "units": "metric"}

    if location.city:
        params["q"] = location.city
    elif location.latitude is not None and location.longitude is not None:
        params["lat"] = location.latitude
        params["lon"] = location.longitude
    else:
        raise ValueError("Location must include either city or latitude+longitude")

    if data_type == "current":
        url = "https://api.openweathermap.org/data/2.5/weather"
    elif data_type == "forecast":
        url = "https://api.openweathermap.org/data/2.5/forecast"
    elif data_type == "historical":
        # Historical data not supported here
        raise NotImplementedError("Historical data_type is not supported")
    else:
        raise ValueError(f"Unsupported data_type: {data_type}")

    return url, params

async def fetch_weather_data(location: Location, data_type: str):
    url, params = build_openweather_url(location, data_type)
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.json()

async def process_entity_job(entity: dict):
    """
    Workflow function for 'entity_job' model.
    Processes the entity before persistence:
    - Fetches weather data based on the entity's location and data_type.
    - Updates entity status and data fields accordingly.
    """

    try:
        request_id = entity.get("request_id", "<unknown>")
        location_dict = entity.get("location", {})
        data_type = entity.get("data_type")

        # Defensive checks
        if not data_type:
            raise ValueError("Entity missing 'data_type'")
        if not location_dict:
            raise ValueError("Entity missing 'location'")

        location = Location(
            city=location_dict.get("city"),
            latitude=location_dict.get("latitude"),
            longitude=location_dict.get("longitude"),
        )

        logger.info(f"[process_entity_job] Processing request {request_id} for location={location} data_type={data_type}")

        # Fetch the weather data asynchronously
        weather_data = await fetch_weather_data(location, data_type)

        # Update entity in-place
        entity["status"] = "completed"
        entity["requestedAt"] = datetime.utcnow().isoformat()
        entity["weather_data"] = weather_data
        entity["error_message"] = None

        logger.info(f"[process_entity_job] Completed request {request_id}")

    except NotImplementedError as nie:
        entity["status"] = "failed"
        entity["requestedAt"] = datetime.utcnow().isoformat()
        entity["weather_data"] = None
        entity["error_message"] = str(nie)
        logger.info(f"[process_entity_job] Request failed: {nie}")

    except (httpx.HTTPStatusError, httpx.RequestError) as http_exc:
        entity["status"] = "failed"
        entity["requestedAt"] = datetime.utcnow().isoformat()
        entity["weather_data"] = None
        entity["error_message"] = f"HTTP error during weather fetch: {str(http_exc)}"
        logger.error(f"[process_entity_job] HTTP error processing request {request_id}: {http_exc}")

    except ValueError as val_err:
        entity["status"] = "failed"
        entity["requestedAt"] = datetime.utcnow().isoformat()
        entity["weather_data"] = None
        entity["error_message"] = f"Invalid input data: {str(val_err)}"
        logger.error(f"[process_entity_job] Validation error processing request {request_id}: {val_err}")

    except Exception as e:
        entity["status"] = "failed"
        entity["requestedAt"] = datetime.utcnow().isoformat()
        entity["weather_data"] = None
        entity["error_message"] = "Failed to fetch or process weather data."
        logger.exception(f"[process_entity_job] Exception processing request {request_id}: {e}")

    return entity

@app.route("/weather/fetch", methods=["POST"])
@validate_request(FetchWeatherRequest)
async def fetch_weather(data: FetchWeatherRequest):
    location = data.location
    if not (location.city or (location.latitude is not None and location.longitude is not None)):
        return jsonify({"message": "Location must include 'city' or both 'latitude' and 'longitude'"}), 400

    request_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()

    entity_data = {
        "request_id": request_id,
        "status": "processing",
        "requestedAt": requested_at,
        "location": {
            "city": location.city,
            "latitude": location.latitude,
            "longitude": location.longitude,
        },
        "data_type": data.data_type,
        "weather_data": None,
        "error_message": None,
    }

    add_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="entity_job",
        entity_version=ENTITY_VERSION,
        entity=entity_data,
        workflow=process_entity_job,
    )

    return jsonify({"request_id": add_id, "status": "processing", "message": "Request accepted"}), 202

@app.route("/weather/result/<request_id>", methods=["GET"])
async def get_weather_result(request_id):
    job = await entity_service.get_item(
        token=cyoda_token,
        entity_model="entity_job",
        entity_version=ENTITY_VERSION,
        technical_id=request_id,
    )
    if not job:
        return jsonify({"message": "Request ID not found"}), 404

    response = {
        "request_id": job.get("request_id", request_id),
        "location": job.get("location"),
        "data_type": job.get("data_type"),
        "status": job.get("status"),
    }

    if job.get("status") == "completed":
        response["weather_data"] = job.get("weather_data")
    elif job.get("status") == "failed":
        response["error_message"] = job.get("error_message")

    return jsonify(response)

if __name__ == '__main__':
    import sys

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s - %(message)s'
    )

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)