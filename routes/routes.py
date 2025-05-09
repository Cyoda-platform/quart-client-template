from dataclasses import dataclass
from typing import Optional

import logging
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
class HelloPostRequest:
    name: Optional[str] = None  # optional string to personalize greeting

@app.route("/hello", methods=["POST"])
@validate_request(HelloPostRequest)
async def post_hello(data: HelloPostRequest):
    job_data = {
        "name": data.name
    }
    job_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="hello_post_request",
        entity_version=ENTITY_VERSION,
        entity=job_data,
        )
    return jsonify({"status": "success", "message": "Hello World processed", "job_id": job_id})

@app.route("/hello", methods=["GET"])
async def get_hello():
    try:
        items = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="hello_post_request",
            entity_version=ENTITY_VERSION,
            condition={"status": "completed"}
        )
        if not items:
            return jsonify({"greeting": "Hello World"})
        latest_item = max(items, key=lambda x: x.get("completedAt") or "")
        greeting = latest_item.get("greeting", "Hello World")
        return jsonify({"greeting": greeting})
    except Exception as e:
        logger.exception(f"Error fetching greeting: {e}")
        return jsonify({"greeting": "Hello World"})

if __name__ == '__main__':
    import sys
    import logging

    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO,
    )

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)