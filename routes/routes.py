from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

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
class WeatherFetchRequest:
    latitude: float
    longitude: float
    parameters: List[str]
    start_date: Optional[str] = None
    end_date: Optional[str] = None

async def fetch_weather_from_api(latitude: float, longitude: float, parameters: list, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
    base_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(parameters)
    }
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(base_url, params=params)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.exception(f"Error fetching weather data from external API: {e}")
            raise

@app.route("/weather/fetch", methods=["POST"])
@validate_request(WeatherFetchRequest)
async def weather_fetch(data: WeatherFetchRequest):
    data_dict = data.__dict__
    try:
        job_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="weather_fetch_request",
            entity_version=ENTITY_VERSION,
            entity=data_dict
        )
    except Exception as e:
        logger.exception(f"Failed to add new weather fetch request: {e}")
        return jsonify({"error": "Failed to create request"}), 500

    return jsonify({"request_id": job_id, "status": "processing"}), 202

@app.route("/weather/result/<string:request_id>", methods=["GET"])
async def weather_result(request_id):
    try:
        job = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="weather_fetch_request",
            entity_version=ENTITY_VERSION,
            technical_id=request_id
        )
    except Exception as e:
        logger.exception(f"Failed to get job {request_id}: {e}")
        return jsonify({"error": "Request ID not found"}), 404

    if not job:
        return jsonify({"error": "Request ID not found"}), 404

    response = {
        "request_id": request_id,
        "status": job.get("status"),
        "requestedAt": job.get("requestedAt"),
    }
    if job.get("status") == "completed":
        response.update({
            "location": job.get("location"),
            "parameters": job.get("parameters"),
            "data": job.get("data"),
            "completedAt": job.get("completedAt"),
        })
    elif job.get("status") == "failed":
        response.update({
            "error": job.get("error"),
            "completedAt": job.get("completedAt"),
        })

    return jsonify(response)

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
