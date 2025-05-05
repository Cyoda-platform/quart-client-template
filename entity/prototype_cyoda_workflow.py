from dataclasses import dataclass
import logging
from datetime import datetime
import uuid
import asyncio

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class CatRequest:
    type: str = "fact"  # Optional, default to "fact"

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

async def fetch_cat_fact(client: httpx.AsyncClient):
    try:
        response = await client.get("https://catfact.ninja/fact", timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("fact")
    except Exception:
        logger.exception("Failed to fetch cat fact")
        return None

async def fetch_cat_image(client: httpx.AsyncClient):
    try:
        response = await client.get("https://api.thecatapi.com/v1/images/search", timeout=10)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            return data[0].get("url")
        return None
    except Exception:
        logger.exception("Failed to fetch cat image")
        return None

async def process_CatJob(entity: dict) -> dict:
    # This workflow function runs asynchronously before persisting the entity
    # It must not call add/update/delete for the same entity_model to avoid recursion
    # It modifies the entity dict in place with processing results and status

    # Validate required keys and set defaults if missing
    entity_type = entity.get("type", "fact")
    if "resultId" not in entity or not entity["resultId"]:
        # Ensure resultId is present for tracking
        entity["resultId"] = str(uuid.uuid4())

    async with httpx.AsyncClient() as client:
        try:
            content = {
                "helloWorldMessage": "Hello World",
                "catData": {}
            }

            if entity_type == "fact":
                fact = await fetch_cat_fact(client)
                if fact:
                    content["catData"]["fact"] = fact

            elif entity_type == "image":
                image_url = await fetch_cat_image(client)
                if image_url:
                    content["catData"]["imageUrl"] = image_url

            elif entity_type == "mixed":
                fact_task = asyncio.create_task(fetch_cat_fact(client))
                image_task = asyncio.create_task(fetch_cat_image(client))
                fact, image_url = await asyncio.gather(fact_task, image_task)
                if fact:
                    content["catData"]["fact"] = fact
                if image_url:
                    content["catData"]["imageUrl"] = image_url

            else:
                # Unknown type, fallback to fact
                fact = await fetch_cat_fact(client)
                if fact:
                    content["catData"]["fact"] = fact

            entity["status"] = "completed"
            entity["result"] = {
                "resultId": entity["resultId"],
                "content": content,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            entity["workflow_processedAt"] = datetime.utcnow().isoformat() + "Z"
        except Exception:
            logger.exception("Error processing CatJob workflow")
            entity["status"] = "failed"
            entity["result"] = {
                "error": "Failed to process request."
            }
            entity["workflow_processedAt"] = datetime.utcnow().isoformat() + "Z"

    return entity

@app.route("/api/cats/hello-world", methods=["POST"])
@validate_request(CatRequest)
async def post_hello_world(data: CatRequest):
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat() + "Z"

    initial_data = {
        "status": "processing",
        "requestedAt": requested_at,
        "result": None,
        "type": data.type,
        "resultId": job_id
    }

    try:
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="CatJob",
            entity_version=ENTITY_VERSION,
            entity=initial_data,
            workflow=process_CatJob
        )
    except Exception:
        logger.exception("Failed to add CatJob entity")
        return jsonify({
            "status": "error",
            "message": "Failed to start processing"
        }), 500

    return jsonify({
        "status": "success",
        "message": "Hello World with cat data fetching started",
        "resultId": job_id
    }), 202

@app.route("/api/cats/result/<result_id>", methods=["GET"])
async def get_result(result_id):
    try:
        data = await entity_service.get_item(
            token=cyoda_token,
            entity_model="CatJob",
            entity_version=ENTITY_VERSION,
            technical_id=result_id
        )
        if not data:
            return jsonify({"error": "Result not found"}), 404

        status = data.get("status", "")
        if status == "processing":
            return jsonify({"status": "processing"}), 202
        if status == "failed":
            return jsonify({"status": "failed", "error": data.get("result", {}).get("error")}), 500

        return jsonify(data.get("result")), 200

    except Exception:
        logger.exception("Failed to retrieve CatJob result")
        return jsonify({"error": "Failed to retrieve result"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)