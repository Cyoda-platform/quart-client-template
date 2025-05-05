from dataclasses import dataclass
from typing import Optional, Union

import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
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


# Helper: build weather API url and params based on data_type
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
        url = f"https://api.openweathermap.org/data/2.5/weather"
    elif data_type == "forecast":
        url = f"https://api.openweathermap.org/data/2.5/forecast"
    elif data_type == "historical":
        # OpenWeather free API does not support historical, so we fallback or mock
        # TODO: Implement historical data with paid API or alternative
        raise NotImplementedError("Historical data_type is not supported in prototype")
    else:
        raise ValueError(f"Unsupported data_type: {data_type}")

    return url, params


async def fetch_weather_data(location: Location, data_type: str):
    url, params = build_openweather_url(location, data_type)
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.json()


async def process_entity(request_id: str, location: Location, data_type: str):
    try:
        logger.info(f"Processing request {request_id} for location={location} data_type={data_type}")
        data = await fetch_weather_data(location, data_type)

        # Prepare entity data to store
        entity_data = {
            "request_id": request_id,
            "status": "completed",
            "requestedAt": datetime.utcnow().isoformat(),
            "location": {
                "city": location.city,
                "latitude": location.latitude,
                "longitude": location.longitude,
            },
            "data_type": data_type,
            "weather_data": data,
            "error_message": None,
        }

        # Store the entity data by calling entity_service.update_item
        # Since add_item was called earlier to get id, here we update by request_id technical_id
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            entity=entity_data,
            technical_id=request_id,
            meta={}
        )

        logger.info(f"Completed request {request_id}")
    except NotImplementedError as nie:
        entity_data = {
            "request_id": request_id,
            "status": "failed",
            "requestedAt": datetime.utcnow().isoformat(),
            "location": {
                "city": location.city,
                "latitude": location.latitude,
                "longitude": location.longitude,
            },
            "data_type": data_type,
            "weather_data": None,
            "error_message": str(nie),
        }
        try:
            await entity_service.update_item(
                token=cyoda_token,
                entity_model="entity_job",
                entity_version=ENTITY_VERSION,
                entity=entity_data,
                technical_id=request_id,
                meta={}
            )
        except Exception as e:
            logger.exception(f"Failed to update entity_job with failure info for request {request_id}: {e}")

        logger.info(f"Request {request_id} failed: {nie}")
    except Exception as e:
        entity_data = {
            "request_id": request_id,
            "status": "failed",
            "requestedAt": datetime.utcnow().isoformat(),
            "location": {
                "city": location.city,
                "latitude": location.latitude,
                "longitude": location.longitude,
            },
            "data_type": data_type,
            "weather_data": None,
            "error_message": "Failed to fetch or process weather data.",
        }
        try:
            await entity_service.update_item(
                token=cyoda_token,
                entity_model="entity_job",
                entity_version=ENTITY_VERSION,
                entity=entity_data,
                technical_id=request_id,
                meta={}
            )
        except Exception as e2:
            logger.exception(f"Failed to update entity_job with failure info for request {request_id}: {e2}")

        logger.exception(f"Exception processing request {request_id}: {e}")


@app.route("/weather/fetch", methods=["POST"])
@validate_request(FetchWeatherRequest)
async def fetch_weather(data: FetchWeatherRequest):
    try:
        location = data.location
        data_type = data.data_type

        # Validate location keys minimally
        if not (location.city or (location.latitude is not None and location.longitude is not None)):
            return jsonify({"message": "Location must include 'city' or both 'latitude' and 'longitude'"}), 400

        request_id = str(uuid.uuid4())
        requested_at = datetime.utcnow().isoformat()

        # Prepare initial entity data with status processing and no weather_data yet
        entity_data = {
            "request_id": request_id,
            "status": "processing",
            "requestedAt": requested_at,
            "location": {
                "city": location.city,
                "latitude": location.latitude,
                "longitude": location.longitude,
            },
            "data_type": data_type,
            "weather_data": None,
            "error_message": None,
        }

        # Add item to entity_service to store initial request and get technical_id
        # Here we use request_id as the technical_id so it can be used later to update
        # entity_service.add_item returns an id, but we want to keep our request_id, so skip replacement if not possible
        # Since requirement says just call add_item and return id, we must call add_item and return id
        # But we want to use request_id as id, so we skip and instead use add_item with entity_data and use returned id
        # So call add_item and get id, but store our request_id in entity_data as well
        add_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            entity=entity_data
        )

        # Fire and forget processing task with add_id as technical_id
        # But our processing uses request_id as technical_id, so we must pass add_id
        asyncio.create_task(process_entity(add_id, location, data_type))

        return jsonify({"request_id": add_id, "status": "processing", "message": "Request accepted"}), 202

    except Exception as e:
        logger.exception(f"Exception in /weather/fetch endpoint: {e}")
        return jsonify({"message": "Internal server error"}), 500


@app.route("/weather/result/<request_id>", methods=["GET"])
async def get_weather_result(request_id):
    try:
        job = await entity_service.get_item(
            token=cyoda_token,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            technical_id=request_id
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
    except Exception as e:
        logger.exception(f"Exception in /weather/result endpoint: {e}")
        return jsonify({"message": "Internal server error"}), 500


if __name__ == '__main__':
    import sys
    import logging.config

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s - %(message)s'
    )

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)