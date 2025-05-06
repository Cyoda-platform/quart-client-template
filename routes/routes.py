from dataclasses import dataclass
import logging
from datetime import datetime

import httpx
from quart import Blueprint, jsonify
from quart_schema import validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

# External APIs URLs
CAT_FACT_API = "https://catfact.ninja/fact"
CAT_IMAGE_API = "https://api.thecatapi.com/v1/images/search"

entity_name = "hello_request"


@dataclass
class HelloRequest:
    type: str  # expected values: "image", "fact", "greeting"


@routes_bp.route("/api/cats/hello", methods=["POST"])
@validate_request(HelloRequest)
async def cats_hello_post(data: HelloRequest):
    """
    Endpoint to add a hello request entity.
    The heavy lifting is done in the workflow function.
    """
    try:
        # Convert dataclass to dict
        entity_data = data.__dict__.copy()

        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=entity_data,
        )
        return jsonify({"id": entity_id})
    except Exception as e:
        logger.exception("Error in cats_hello_post: %s", e)
        return jsonify({"message": "Internal server error", "data": None}), 500


@routes_bp.route("/api/cats/hello/result", methods=["GET"])
async def cats_hello_get():
    """
    Returns the most recent hello_request entity.
    """
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
        )
        if not items:
            return (
                jsonify(
                    {"message": "No results available yet", "data": None, "timestamp": None}
                ),
                404,
            )

        # Sorting to get the latest by timestamp safely
        def get_timestamp(item):
            ts = item.get("timestamp")
            if not ts:
                return ""
            return ts

        sorted_items = sorted(items, key=get_timestamp, reverse=True)
        latest = sorted_items[0]
        # Defensive copy to avoid accidental mutation
        result = dict(latest)
        return jsonify(result)
    except Exception as e:
        logger.exception("Error in cats_hello_get: %s", e)
        return jsonify({"message": "Internal server error", "data": None}), 500