from dataclasses import dataclass
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify
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

@dataclass
class CatFetchRequest:
    type: str  # "image" or "fact"

# Workflow function to process CatFetchRequest entity before persistence
async def process_catfetchrequest(entity: dict):
    """
    Workflow function applied to CatFetchRequest entity asynchronously before persistence.
    It fetches the requested data ('image' or 'fact') and updates the entity in-place.
    """
    # Initialize state safely
    try:
        entity.setdefault("status", "processing")
        entity.setdefault("data", None)
        if "requestedAt" not in entity:
            entity["requestedAt"] = datetime.utcnow().isoformat() + "Z"

        requested_type = entity.get("type")
        if requested_type not in ("image", "fact"):
            entity["status"] = "failed"
            entity["data"] = "Invalid type requested"
            logger.warning(f"Invalid type in workflow: {requested_type}")
            return

        async def fetch_cat_image() -> str:
            url = "https://api.thecatapi.com/v1/images/search"
            async with httpx.AsyncClient() as client:
                try:
                    resp = await client.get(url, timeout=10)
                    resp.raise_for_status()
                    data = resp.json()
                    if isinstance(data, list) and data and "url" in data[0]:
                        return data[0]["url"]
                    logger.warning("Unexpected response structure from cat image API")
                    return ""
                except Exception as e:
                    logger.exception(f"Error fetching cat image: {e}")
                    return ""

        async def fetch_cat_fact() -> str:
            url = "https://catfact.ninja/fact"
            async with httpx.AsyncClient() as client:
                try:
                    resp = await client.get(url, timeout=10)
                    resp.raise_for_status()
                    data = resp.json()
                    fact = data.get("fact") if isinstance(data, dict) else None
                    if fact:
                        return fact
                    logger.warning("Unexpected response structure from cat fact API")
                    return ""
                except Exception as e:
                    logger.exception(f"Error fetching cat fact: {e}")
                    return ""

        # Fetch data according to type
        if requested_type == "image":
            result = await fetch_cat_image()
        else:  # "fact"
            result = await fetch_cat_fact()

        if not result:
            entity["status"] = "failed"
            entity["data"] = "Failed to fetch data"
        else:
            entity["status"] = "completed"
            entity["data"] = result

    except Exception as e:
        logger.exception(f"Exception in workflow process_catfetchrequest: {e}")
        entity["status"] = "failed"
        entity["data"] = "Exception during workflow execution"


@app.route("/cats/fetch", methods=["POST"])
@validate_request(CatFetchRequest)
async def cats_fetch(data: CatFetchRequest):
    """
    POST /cats/fetch
    Request JSON: { "type": "image" | "fact" }
    Response JSON: { "requestId": "string" }
    """
    try:
        # Validate input explicitly even if dataclass is used
        if data.type not in ("image", "fact"):
            return jsonify({"error": "Invalid type. Must be 'image' or 'fact'."}), 400

        # Prepare a minimal entity dict for persistence
        entity_dict = {
            "type": data.type,
        }

        # Add item with workflow function - processing happens inside workflow
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="CatFetchRequest",
            entity_version=ENTITY_VERSION,
            entity=entity_dict,
            workflow=process_catfetchrequest
        )

        return jsonify({"requestId": entity_id})

    except Exception as e:
        logger.exception(f"Error in /cats/fetch endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/cats/result/<string:request_id>", methods=["GET"])
async def cats_result(request_id: str):
    """
    GET /cats/result/{requestId}
    Response JSON:
    {
      "requestId": "string",
      "type": "image" | "fact",
      "data": "string",
      "status": "processing" | "completed" | "failed",
      "requestedAt": "ISO8601 string"
    }
    """
    try:
        entity = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="CatFetchRequest",
            entity_version=ENTITY_VERSION,
            entity_id=request_id,
        )
        if entity is None:
            return jsonify({"error": "requestId not found"}), 404

        # Defensive defaults
        response = {
            "requestId": request_id,
            "type": entity.get("type", "unknown"),
            "data": entity.get("data"),
            "status": entity.get("status", "processing"),
            "requestedAt": entity.get("requestedAt"),
        }
        return jsonify(response)

    except Exception as e:
        logger.exception(f"Error in /cats/result/{request_id} endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)