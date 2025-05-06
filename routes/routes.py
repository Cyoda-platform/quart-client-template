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