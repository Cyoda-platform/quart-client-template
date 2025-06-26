import asyncio
import logging
import sys
from dataclasses import dataclass
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

# Request dataclass for POST /weather/fetch
@dataclass
class WeatherFetchRequest:
    latitude: float
    longitude: float
    parameters: list[str]
    start_date: str
    end_date: str

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

async def fetch_weather_data(latitude, longitude, parameters, start_date, end_date):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(parameters),
        "timezone": "auto",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(OPEN_METEO_URL, params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.exception(f"Error while calling Open-Meteo API: {e}")
            raise

async def process_entity(technical_id: str, data: WeatherFetchRequest):
    try:
        raw_weather = await fetch_weather_data(
            data.latitude, data.longitude, data.parameters, data.start_date, data.end_date
        )
        hourly_data = raw_weather.get("hourly", {})
        filtered_data = {param: hourly_data.get(param, []) for param in data.parameters}

        # update item with results and status completed
        update_data = {
            "status": "completed",
            "result": {
                "request_id": technical_id,
                "latitude": data.latitude,
                "longitude": data.longitude,
                "data": filtered_data,
                "date_range": {"start": data.start_date, "end": data.end_date},
            },
            "completedAt": datetime.utcnow().isoformat() + "Z",
        }
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="weather_fetch",
            entity_version=ENTITY_VERSION,
            entity=update_data,
            technical_id=technical_id,
            meta={},
        )
        logger.info(f"Job {technical_id} completed successfully")
    except Exception as e:
        update_data = {"status": "failed", "error": str(e)}
        try:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="weather_fetch",
                entity_version=ENTITY_VERSION,
                entity=update_data,
                technical_id=technical_id,
                meta={},
            )
        except Exception as ex:
            logger.exception(f"Failed to update job {technical_id} with failure status: {ex}")
        logger.exception(f"Job {technical_id} failed")

@app.route("/weather/fetch", methods=["POST"])
@validate_request(WeatherFetchRequest)  # workaround: validation last for POST due to quart-schema issue
async def weather_fetch(data: WeatherFetchRequest):
    technical_id = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    initial_data = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat() + "Z",
    }
    # Add item to entity_service, must await id returned (here we use generated technical_id as id)
    # Since id is generated outside, we simulate add_item by forcing id usage
    # But as per instructions, must use add_item to add and get id; but original code generates id outside
    # So here we add the item without id param to get the id from service (but this will differ from our technical_id)
    # To keep technical_id consistent, we accept the string from add_item (but instructions say id is string)
    # So we use add_item and ignore our generated technical_id, and pass data with status processing
    try:
        id_returned = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="weather_fetch",
            entity_version=ENTITY_VERSION,
            entity=initial_data,
        )
        # start background task with returned id string
        asyncio.create_task(process_entity(str(id_returned), data))
        return jsonify(
            {
                "status": "success",
                "message": "Weather data fetch initiated",
                "request_id": str(id_returned),
            }
        )
    except Exception as e:
        logger.exception(f"Failed to initiate weather fetch: {e}")
        return jsonify({"status": "error", "message": "Failed to initiate weather fetch"}), 500

@app.route("/weather/result/<string:technical_id>", methods=["GET"])
async def weather_result(technical_id: str):
    try:
        job = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="weather_fetch",
            entity_version=ENTITY_VERSION,
            technical_id=technical_id,
        )
        if not job:
            return jsonify({"status": "error", "message": "Request ID not found"}), 404
        status = job.get("status")
        if status == "processing":
            return jsonify({"status": "processing", "message": "Data is still being fetched"}), 202
        if status == "failed":
            return jsonify({"status": "failed", "message": job.get("error", "Unknown error")}), 500
        return jsonify(job.get("result", {}))
    except Exception as e:
        logger.exception(f"Error retrieving job result for {technical_id}: {e}")
        return jsonify({"status": "error", "message": "Failed to retrieve data"}), 500

if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)