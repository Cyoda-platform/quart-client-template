import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, Optional

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
class CatEvent:
    catId: Optional[str] = None
    eventType: str
    intensity: str

NOTIFICATION_WEBHOOK_URL = "https://httpbin.org/post"

async def send_notification(message: str) -> bool:
    async with httpx.AsyncClient() as client:
        try:
            payload = {"message": message}
            response = await client.post(NOTIFICATION_WEBHOOK_URL, json=payload, timeout=5)
            response.raise_for_status()
            logger.info(f"Notification sent: {message}")
            return True
        except Exception as e:
            logger.exception(f"Failed to send notification: {e}")
            return False

async def process_cat_event(entity: Dict[str, Any]) -> None:
    """
    Workflow function applied to 'cat_event' entity before persistence.
    Modifies entity state, sends notifications, and adds supplementary data entities.
    """
    # Add timestamp to the entity
    entity["timestamp"] = datetime.now(timezone.utc).isoformat()

    # Check event type and intensity for notification
    if entity.get("eventType") == "food_request" and entity.get("intensity", "").lower() == "dramatic":
        message = "Emergency! A cat demands snacks"
        notification_sent = await send_notification(message)

        # Add notification record as supplementary entity (different entity_model)
        notification_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": message,
        }
        try:
            # Add notification entity (different model to avoid recursion)
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="notification",
                entity_version=ENTITY_VERSION,
                entity=notification_record,
                workflow=None  # no workflow for notifications
            )
        except Exception:
            logger.exception("Failed to add notification entity")

        # Add notification info to the current entity state to persist
        entity["notificationSent"] = notification_sent
        entity["notificationMessage"] = message
    else:
        # No notification sent, clean fields just in case
        entity["notificationSent"] = False
        entity["notificationMessage"] = ""

@app.route("/events/cat-demand", methods=["POST"])
@validate_request(CatEvent)  # workaround: validation must go after route for POST due to quart-schema issue
async def cat_demand_event(data: CatEvent):
    try:
        # Pass the workflow function as argument
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="cat_event",
            entity_version=ENTITY_VERSION,
            entity=data.__dict__,
            workflow=process_cat_event
        )

        # Fetch the persisted entity to include notification fields and timestamp in response
        persisted_entity = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="cat_event",
            entity_version=ENTITY_VERSION,
            technical_id=entity_id
        )

        if persisted_entity is None:
            # Defensive: item should exist, but handle gracefully
            return jsonify({"error": "Item not found after creation"}), 500

        # Return the persisted entity plus its ID
        response = {
            "id": entity_id,
            "eventProcessed": persisted_entity
        }
        return jsonify(response)

    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500

@app.route("/events/cat-demand/<string:item_id>", methods=["GET"])
async def get_cat_event(item_id: str):
    try:
        item = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="cat_event",
            entity_version=ENTITY_VERSION,
            technical_id=item_id
        )
        if item is None:
            return jsonify({"error": "Item not found"}), 404
        return jsonify(item)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)