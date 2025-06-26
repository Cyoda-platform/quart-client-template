from dataclasses import dataclass
import logging
from datetime import datetime
from typing import Dict, Any, Callable

import httpx
from quart import Blueprint, jsonify, request
from quart_schema import validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

routes_bp = Blueprint('routes', __name__)

notifications_store: Dict[str, list] = {}
entity_jobs: Dict[str, dict] = {}

OPENAI_API_KEY = "your_openai_api_key_here"  # TODO: replace with environment variable in production
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

@dataclass
class EventDetectRequest:
    cat_id: str
    input_type: str
    input_data: str

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

async def process_event_detect(entity: Dict[str, Any]) -> None:
    cat_id = entity.get("cat_id")
    input_type = entity.get("input_type")
    input_data = entity.get("input_data")
    event_id = entity.get("event_id") or f"{cat_id}-{datetime.utcnow().timestamp()}"

    entity_jobs[event_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat()
    }

    try:
        event_detected = False
        event_type = None
        message = None

        if input_type == "text":
            event_detected = await analyze_text_for_food_request(input_data)
        else:
            logger.info(f"Input type '{input_type}' is not supported yet for event detection.")

        if event_detected:
            event_type = "food_request"
            message = "Emergency! A cat demands snacks"
            timestamp = datetime.utcnow().isoformat()

            notification_entity = {
                "cat_id": cat_id,
                "timestamp": timestamp,
                "message": message
            }

            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="notification",
                entity_version=ENTITY_VERSION,
                entity=notification_entity
            )

            logger.info(f"Notification added for cat_id={cat_id}: {message}")

        entity["event_detected"] = event_detected
        entity["event_type"] = event_type
        entity["message"] = message
        entity["processed_at"] = datetime.utcnow().isoformat()

        entity_jobs[event_id]["status"] = "completed"
        entity_jobs[event_id]["result"] = {
            "event_detected": event_detected,
            "event_type": event_type,
            "message": message
        }

    except Exception as e:
        logger.exception(f"Error in event_detect workflow: {e}")
        entity_jobs[event_id]["status"] = "failed"
        entity_jobs[event_id]["result"] = {
            "event_detected": False,
            "event_type": None,
            "message": None,
            "error": str(e)
        }

async def process_example_entity(entity: Dict[str, Any]) -> None:
    entity['processed_at'] = datetime.utcnow().isoformat()
    logger.info(f"Processed example_entity workflow: {entity}")

@routes_bp.route("/entity/<string:entity_name>", methods=["POST"])
async def add_entity(entity_name: str):
    try:
        data = await request.get_json()
        if not isinstance(data, dict):
            return jsonify({"error": "Invalid JSON data, expected object"}), 400

        if entity_name.lower() == "event_detect":
            data.setdefault("event_id", f"{data.get('cat_id', 'unknown')}-{datetime.utcnow().timestamp()}")

        workflow_func_name = f"process_{entity_name.lower()}"
        workflow_func: Callable[[Dict[str, Any]], Any] = globals().get(workflow_func_name)

        if workflow_func is None:
            async def noop_workflow(entity: Dict[str, Any]):
                pass
            workflow_func = noop_workflow

        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name.lower(),
            entity_version=ENTITY_VERSION,
            entity=data
        )

        return jsonify({"status": "success", "entity_id": entity_id}), 201

    except Exception as e:
        logger.exception(f"Error adding entity '{entity_name}': {e}")
        return jsonify({"error": "Internal server error"}), 500

@routes_bp.route("/events/detect", methods=["POST"])
@validate_request(EventDetectRequest)
async def detect_event(data: EventDetectRequest):
    entity_data = {
        "cat_id": data.cat_id,
        "input_type": data.input_type,
        "input_data": data.input_data,
        "event_id": f"{data.cat_id}-{datetime.utcnow().timestamp()}"
    }

    entity_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="event_detect",
        entity_version=ENTITY_VERSION,
        entity=entity_data
    )

    return jsonify({"status": "success", "entity_id": entity_id}), 200