from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
import uuid

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

import httpx
from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

ENTITY_VERSION = None
from common.config.config import ENTITY_VERSION

@dataclass
class FetchWeatherRequest:
    location: str
    parameters: list
    date: str = None

async def fetch_weather_from_msgeomet(location: str, parameters: list, date: str = None):
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            url = f"https://api.meteo.lt/v1/places/{location}/forecasts/long-term"
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            forecasts = data.get("forecastTimestamps", [])
            if not forecasts:
                return {}
            forecast = forecasts[0]
            extracted = {}
            if "temperature" in parameters and "airTemperature" in forecast:
                extracted["temperature"] = forecast["airTemperature"]
            if "humidity" in parameters and "relativeHumidity" in forecast:
                extracted["humidity"] = forecast["relativeHumidity"]
            if "wind_speed" in parameters and "windSpeed" in forecast:
                extracted["wind_speed"] = forecast["windSpeed"]
            return extracted
        except Exception as e:
            logger.exception(f"Error fetching weather from MSC GeoMet: {e}")
            return None

async def process_entity(job_id: str, location: str, parameters: list, date: str):
    try:
        # Update status to processing
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id,
            entity={"status": "processing"},
            meta={}
        )
        data = await fetch_weather_from_msgeomet(location, parameters, date)
        if data is None:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="entity_job",
                entity_version=ENTITY_VERSION,
                technical_id=job_id,
                entity={"status": "error", "result": {}},
                meta={}
            )
        else:
            result_data = {
                "status": "completed",
                "result": {
                    "location": location,
                    "parameters": data,
                    "date": date if date else datetime.utcnow().strftime("%Y-%m-%d"),
                    "retrieved_at": datetime.utcnow().isoformat() + "Z",
                }
            }
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="entity_job",
                entity_version=ENTITY_VERSION,
                technical_id=job_id,
                entity=result_data,
                meta={}
            )
    except Exception as e:
        logger.exception(e)
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id,
            entity={"status": "error", "result": {}},
            meta={}
        )

@app.route("/weather/fetch", methods=["POST"])
@validate_request(FetchWeatherRequest)
async def fetch_weather(data: FetchWeatherRequest):
    location = data.location
    parameters = data.parameters
    date = data.date
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat() + "Z"
    # Store initial job info by adding item to entity_service
    await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="entity_job",
        entity_version=ENTITY_VERSION,
        entity={
            "status": "queued",
            "requestedAt": requested_at
        }
    )
    # Note: add_item returns id, but here we want to keep generated UUID as id, so we save manually with that id:
    # Instead of add_item, we do update_item with technical_id=job_id, so we keep that UUID as id:
    await entity_service.update_item(
        token=cyoda_auth_service,
        entity_model="entity_job",
        entity_version=ENTITY_VERSION,
        technical_id=job_id,
        entity={
            "status": "queued",
            "requestedAt": requested_at
        },
        meta={}
    )
    asyncio.create_task(process_entity(job_id, location, parameters, date))
    return jsonify({
        "status": "success",
        "fetch_id": job_id,
        "message": "Data fetching started"
    })

@app.route("/weather/result/<string:fetch_id>", methods=["GET"])
async def get_result(fetch_id: str):
    job = await entity_service.get_item(
        token=cyoda_auth_service,
        entity_model="entity_job",
        entity_version=ENTITY_VERSION,
        technical_id=fetch_id
    )
    if not job:
        return jsonify({"status": "error", "message": "fetch_id not found"}), 404
    if job.get("status") in ("processing", "queued"):
        return jsonify({"status": "processing", "message": "Result not ready yet"}), 202
    if job.get("status") == "error":
        return jsonify({"status": "error", "message": "Failed to fetch data"}), 500
    return jsonify({
        "fetch_id": fetch_id,
        **job.get("result", {}),
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)