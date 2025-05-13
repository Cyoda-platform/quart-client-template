from datetime import datetime
import logging
from quart import Blueprint, jsonify, request
from quart_schema import validate_request, validate_querystring

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

entity_name_cache = "weather_cache"
entity_name_job = "weather_fetch_job"

MSC_GEOMET_BASE_URL = "https://api.msc-geomet.com/weather"  # TODO: replace with actual URL


@routes_bp.route("/weather/fetch", methods=["POST"])
@validate_request
async def weather_fetch(data):
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


@routes_bp.route("/weather/results", methods=["GET"])
@validate_querystring
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