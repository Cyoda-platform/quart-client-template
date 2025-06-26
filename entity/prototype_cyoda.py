from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

# Dataclasses for request validation
@dataclass
class EventDetectRequest:
    cat_id: str
    input_type: str
    input_data: str

# In-memory mock persistence for notifications per cat_id
notifications_store: Dict[str, List[Dict]] = {}
entity_jobs: Dict[str, Dict] = {}

OPENAI_API_KEY = "your_openai_api_key_here"  # TODO: replace with env var
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

async def analyze_text_for_food_request(text: str) -> bool:
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an assistant that detects if a cat is dramatically requesting food. "
                    "Return 'yes' if the input text shows a dramatic food request, otherwise 'no'."
                )
            },
            {
                "role": "user",
                "content": text
            }
        ],
        "max_tokens": 5,
        "temperature": 0
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(OPENAI_API_URL, json=data, headers=headers, timeout=10)
            response.raise_for_status()
            result = response.json()
            answer = result["choices"][0]["message"]["content"].strip().lower()
            return answer == "yes"
        except Exception as e:
            logger.exception(f"Error calling OpenAI API: {e}")
            return False

async def process_event_detection(event_id: str, cat_id: str, input_type: str, input_data: str):
    try:
        event_detected = False
        event_type = None
        message = None

        if input_type == "text":
            event_detected = await analyze_text_for_food_request(input_data)
        else:
            logger.info(f"Input type '{input_type}' is not supported yet for event detection.")
            event_detected = False

        if event_detected:
            event_type = "food_request"
            message = "Emergency! A cat demands snacks"
            timestamp = datetime.utcnow().isoformat()
            notifications_store.setdefault(cat_id, []).append({
                "timestamp": timestamp,
                "message": message
            })
            logger.info(f"Notification sent for cat_id={cat_id}: {message}")

        entity_jobs[event_id]["status"] = "completed"
        entity_jobs[event_id]["result"] = {
            "event_detected": event_detected,
            "event_type": event_type,
            "message": message
        }
    except Exception as e:
        logger.exception(f"Error processing event detection for job {event_id}: {e}")
        entity_jobs[event_id]["status"] = "failed"
        entity_jobs[event_id]["result"] = {
            "event_detected": False,
            "event_type": None,
            "message": None
        }

@app.route("/events/detect", methods=["POST"])
@validate_request(EventDetectRequest)  # validation last for POST (workaround for quart-schema issue)
async def detect_event(data: EventDetectRequest):
    cat_id = data.cat_id
    input_type = data.input_type
    input_data = data.input_data

    event_id = f"{cat_id}-{datetime.utcnow().timestamp()}"
    entity_jobs[event_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat()
    }

    # Process event detection synchronously to return success after notification
    await process_event_detection(event_id, cat_id, input_type, input_data)

    # Always return success if event received and notification sent
    return jsonify({"status": "success"}), 200

# Example of replacing an entity CRUD endpoint with entity_service usage for reference
# Since original code does not have entity endpoints, here is an example template:

# from quart import request, jsonify
# @app.route("/entity/<string:id>", methods=["GET"])
# async def get_entity(id: str):
#     try:
#         entity_name = "entity_name"  # replace with your entity name in underscore lowercase
#         item = await entity_service.get_item(
#             token=cyoda_auth_service,
#             entity_model=entity_name,
#             entity_version=ENTITY_VERSION,
#             technical_id=id
#         )
#         if item is None:
#             return jsonify({"error": "Not found"}), 404
#         return jsonify(item), 200
#     except Exception as e:
#         logger.exception(e)
#         return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)