from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

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


async def fetch_cat_fact(client: httpx.AsyncClient) -> str:
    try:
        resp = await client.get(CAT_FACT_API, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        fact = data.get("fact")
        if not fact:
            logger.warning("Cat fact API returned no fact")
            return "No fact available"
        return fact
    except Exception as e:
        logger.exception("Failed to fetch cat fact: %s", e)
        return "Failed to fetch cat fact"


async def fetch_cat_image_url(client: httpx.AsyncClient) -> str:
    try:
        resp = await client.get(CAT_IMAGE_API, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and data:
            url = data[0].get("url")
            if url:
                return url
        logger.warning("Cat image API returned unexpected data format")
        return ""
    except Exception as e:
        logger.exception("Failed to fetch cat image: %s", e)
        return ""


async def process_hello_request(entity: dict) -> None:
    """
    Workflow function applied to the entity asynchronously before persistence.
    Modifies the entity dict in place by adding message, data, and timestamp.
    """
    async with httpx.AsyncClient() as client:
        cat_type = entity.get("type", "greeting")
        message = "Hello, Cat Lover!"
        cat_data = None

        if cat_type == "fact":
            cat_data = await fetch_cat_fact(client)
        elif cat_type == "image":
            cat_data = await fetch_cat_image_url(client)
        elif cat_type == "greeting":
            cat_data = None
        else:
            # Unknown type fallback to greeting behavior
            logger.warning("Unknown type received in hello_request: %s", cat_type)
            cat_data = None

        # Modify entity directly for persistence
        entity["message"] = message
        entity["data"] = cat_data
        entity["timestamp"] = datetime.utcnow().isoformat() + "Z"


@app.route("/api/cats/hello", methods=["POST"])
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
            workflow=process_hello_request  # pass the workflow function here
        )
        return jsonify({"id": entity_id})
    except Exception as e:
        logger.exception("Error in cats_hello_post: %s", e)
        return jsonify({"message": "Internal server error", "data": None}), 500


@app.route("/api/cats/hello/result", methods=["GET"])
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


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        level=logging.INFO,
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)