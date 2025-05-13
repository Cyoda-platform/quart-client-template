 import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class FetchRequest:
    locations: list  # List of {"latitude": float, "longitude": float}

@dataclass
class WeatherQuery:
    lat: float
    lon: float

entity_name_cache = "weather_cache"
entity_name_job = "weather_fetch_job"

MSC_GEOMET_BASE_URL = "https://api.msc-geomet.com/weather"  # TODO: replace with actual URL


async def fetch_weather_data(lat: float, lon: float) -> Dict:
    async with httpx.AsyncClient() as client:
        params = {"lat": lat, "lon": lon}
        response = await client.get(MSC_GEOMET_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        return response.json()


async def process_weather_cache(entity: dict) -> dict:
    lat = entity.get("latitude")
    lon = entity.get("longitude")
    if lat is None or lon is None:
        logger.warning("process_weather_cache: latitude or longitude missing in entity")
        return entity
    try:
        data = await fetch_weather_data(lat, lon)
        entity["data"] = data
        entity["timestamp"] = datetime.utcnow().isoformat() + "Z"
        entity["processed_at"] = datetime.utcnow().isoformat() + "Z"
        # Clear any previous fetch errors on success
        entity.pop("fetch_error", None)
        logger.info(f"Weather data fetched and updated for ({lat}, {lon})")
    except Exception as e:
        logger.exception(f"Failed to fetch weather data in process_weather_cache: {e}")
        entity["fetch_error"] = str(e)
    return entity


async def process_weather_fetch_job(entity: dict) -> dict:
    job_id = entity.get("job_id")
    locations = entity.get("locations", [])
    if not job_id or not isinstance(locations, list) or not locations:
        entity["status"] = "failed"
        entity["error"] = "Invalid job_id or locations data"
        logger.error(f"process_weather_fetch_job: invalid input for job: {entity}")
        return entity

    entity["status"] = "processing"
    entity["started_at"] = datetime.utcnow().isoformat() + "Z"

    logger.info(f"Starting job {job_id} for {len(locations)} locations")

    for loc in locations:
        lat = loc.get("latitude")
        lon = loc.get("longitude")
        if lat is None or lon is None:
            logger.warning(f"Skipping location with missing coordinates: {loc}")
            continue

        technical_id = f"{lat}_{lon}"
        cache_entity = {
            "latitude": lat,
            "longitude": lon,
        }

        try:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model=entity_name_cache,
                entity_version=ENTITY_VERSION,
                entity=cache_entity,
                technical_id=technical_id,
                meta={},
            )
            logger.info(f"Updated existing cache entity for ({lat},{lon})")
        except Exception:
            try:
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model=entity_name_cache,
                    entity_version=ENTITY_VERSION,
                    entity=cache_entity,
                )
                logger.info(f"Added new cache entity for ({lat},{lon})")
            except Exception as e:
                logger.exception(f"Failed to add cache entity for ({lat},{lon}): {e}")
                # Continue processing other locations even if one fails

    entity["status"] = "done"
    entity["finished_at"] = datetime.utcnow().isoformat() + "Z"
    logger.info(f"Job {job_id} processing complete")

    return entity


@app.route("/weather/fetch", methods=["POST"])
@validate_request(FetchRequest)
async def weather_fetch(data: FetchRequest):
    locations = data.locations
    if not isinstance(locations, list) or not locations:
        return jsonify({"status": "error", "message": "No locations provided"}), 400

    job_id = f"job_{int(datetime.utcnow().timestamp() * 1000)}"
    job_entity = {
        "job_id": job_id,
        "locations": locations,
        "status": "new",
        "requested_at": datetime.utcnow().isoformat() + "Z",
    }

    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name_job,
            entity_version=ENTITY_VERSION,
            entity=job_entity,
        )
    except Exception as e:
        logger.exception(f"Failed to create fetch job entity: {e}")
        return jsonify({"status": "error", "message": "Failed to create fetch job"}), 500

    return jsonify(
        {
            "status": "success",
            "message": "Weather data fetching job created",
            "job_id": job_id,
            "requested_locations": len(locations),
        }
    )


@validate_querystring(WeatherQuery)
@app.route("/weather/results", methods=["GET"])
async def weather_results():
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    if lat is None or lon is None:
        return jsonify({"status": "error", "message": "lat and lon query parameters required"}), 400

    technical_id = f"{lat}_{lon}"
    try:
        cached = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=entity_name_cache,
            entity_version=ENTITY_VERSION,
            technical_id=technical_id,
        )
    except Exception as e:
        logger.exception(f"Failed to get cached weather data for ({lat}, {lon}): {e}")
        cached = None

    if not cached:
        return (
            jsonify(
                {"status": "error", "message": "No weather data found for the requested location"}
            ),
            404,
        )

    return jsonify(
        {
            "location": {"latitude": lat, "longitude": lon},
            "weather": cached.get("data"),
            "timestamp": cached.get("timestamp"),
        }
    )


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)