from dataclasses import dataclass
import logging
from datetime import datetime
from typing import Optional

import httpx
from quart import Quart, jsonify
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

async def process_cat_hello_entity(entity: dict) -> dict:
    """
    Workflow function to process cat_hello_entity.
    Modifies entity state asynchronously before persistence.
    """
    try:
        # Avoid re-processing entities not in "processing" state
        if entity.get("status") != "processing":
            return entity

        entity["workflow_processedAt"] = datetime.utcnow().isoformat() + "Z"

        cat_type = entity.get("input", {}).get("type", "fact")

        async with httpx.AsyncClient(timeout=10.0) as client:
            if cat_type == "image":
                cat_data = await fetch_cat_image_url(client)
            else:
                cat_data = await fetch_cat_fact(client)

        result = {
            "message": "Hello World",
            "catData": cat_data
        }

        # Update entity to done status with result and timestamp
        entity.update({
            "status": "done",
            "result": result,
            "completedAt": datetime.utcnow().isoformat() + "Z"
        })

        return entity

    except Exception as e:
        logger.exception("Exception in workflow function process_cat_hello_entity")
        # Mark entity as failed with error info and timestamp
        entity.update({
            "status": "failed",
            "error": str(e),
            "completedAt": datetime.utcnow().isoformat() + "Z"
        })
        return entity

@app.route("/api/cat/hello", methods=["POST"])
@validate_request(CatRequest)
async def cat_hello_post(data: CatRequest):
    try:
        cat_type = data.type or "fact"
        if cat_type not in ["fact", "image"]:
            return jsonify({"error": "Invalid type value, must be 'fact' or 'image'"}), 400

        entity_job = {
            "status": "processing",
            "requestedAt": datetime.utcnow().isoformat() + "Z",
            "input": data.__dict__
        }

        technical_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=entity_job,
            workflow=process_cat_hello_entity
        )

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
    try:
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
        done_items.sort(key=lambda x: x.get("completedAt", ""), reverse=True)
        latest_result = done_items[0].get("result", {})
        return jsonify(latest_result)

    except Exception as e:
        logger.exception("Exception in GET /api/cat/hello/latest")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)