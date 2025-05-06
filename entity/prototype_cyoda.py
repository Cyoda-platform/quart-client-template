from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

import sys
from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

@dataclass
class CatRequest:
    type: Optional[str] = "fact"  # "fact" or "image"

ENTITY_NAME = "cat_hello_entity"

# External APIs
CAT_FACT_API = "https://catfact.ninja/fact"
CAT_IMAGE_API = "https://api.thecatapi.com/v1/images/search"

async def fetch_cat_fact(client: httpx.AsyncClient) -> str:
    try:
        resp = await client.get(CAT_FACT_API)
        resp.raise_for_status()
        data = resp.json()
        return data.get("fact", "No fact found.")
    except Exception as e:
        logger.exception("Failed to fetch cat fact")
        return "Failed to retrieve cat fact."

async def fetch_cat_image_url(client: httpx.AsyncClient) -> str:
    try:
        resp = await client.get(CAT_IMAGE_API)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            return data[0].get("url", "No image URL found.")
        return "No image URL found."
    except Exception as e:
        logger.exception("Failed to fetch cat image")
        return "Failed to retrieve cat image."

async def process_entity(technical_id: str, data: dict):
    """
    Simulate processing job: call external API, compose result, update entity_job.
    """
    try:
        async with httpx.AsyncClient() as client:
            cat_type = data.get("type", "fact")
            result = {"message": "Hello World", "catData": None}

            if cat_type == "image":
                cat_data = await fetch_cat_image_url(client)
            else:
                cat_data = await fetch_cat_fact(client)

            result["catData"] = cat_data

            update_data = {
                "status": "done",
                "result": result,
                "completedAt": datetime.utcnow().isoformat() + "Z"
            }

            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model=ENTITY_NAME,
                entity_version=ENTITY_VERSION,
                entity=update_data,
                technical_id=technical_id,
                meta={}
            )
            logger.info(f"Processing finished and entity updated for id {technical_id}")
    except Exception as e:
        logger.exception(f"Exception in processing entity id {technical_id}")

@app.route("/api/cat/hello", methods=["POST"])
@validate_request(CatRequest)  # validation must be last decorator in POST due to quart-schema issue workaround
async def cat_hello_post(data: CatRequest):
    """
    POST endpoint to trigger external data retrieval and compose "Hello World" + cat data.
    Business logic happens here.
    """
    try:
        cat_type = data.type or "fact"
        if cat_type not in ["fact", "image"]:
            return jsonify({"error": "Invalid type value, must be 'fact' or 'image'"}), 400

        # Initialize entity job data with status processing and requestedAt
        entity_job = {
            "status": "processing",
            "requestedAt": datetime.utcnow().isoformat() + "Z",
            "input": data.__dict__
        }

        # Add item to entity_service, returns technical_id
        technical_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=entity_job
        )

        # Fire and forget processing task to update entity_job later
        asyncio.create_task(process_entity(technical_id, data.__dict__))

        # Return immediate response indicating processing started with id
        return jsonify({
            "status": "processing",
            "message": "Request accepted and processing started",
            "id": technical_id
        }), 202
    except Exception as e:
        logger.exception("Exception in POST /api/cat/hello")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/api/cat/hello/latest", methods=["GET"])
async def cat_hello_get_latest():
    """
    GET endpoint to return last stored "Hello World" + cat data result.
    No external calls here, just cached response.
    """
    try:
        # Retrieve all items and find the latest done by completedAt timestamp
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION
        )
        done_items = [item for item in items if item.get("status") == "done" and "result" in item]
        if not done_items:
            return jsonify({
                "message": "No data available yet, please POST /api/cat/hello first"
            }), 404
        # Sort by completedAt descending
        done_items.sort(key=lambda x: x.get("completedAt", ""), reverse=True)
        latest_result = done_items[0].get("result", {})
        return jsonify(latest_result)
    except Exception as e:
        logger.exception("Exception in GET /api/cat/hello/latest")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    import logging

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)