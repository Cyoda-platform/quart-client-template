import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

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

@dataclass
class OrderEvent:
    event_type: str    # "created", "updated", "canceled"
    order_id: str
    cat_type: str      # e.g. "siamese", "persian"
    quantity: int
    price: float
    timestamp: str     # ISO 8601 datetime

CAT_FACTS_API = "https://catfact.ninja/fact"

async def fetch_cat_fact() -> Optional[str]:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(CAT_FACTS_API, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            fact = data.get("fact")
            if isinstance(fact, str) and fact.strip():
                return fact.strip()
            else:
                logger.warning("Received cat fact is empty or invalid")
                return None
        except Exception:
            logger.exception("Failed to fetch cat fact from external API")
            return None

async def process_order(entity: dict) -> dict:
    """
    Workflow function that modifies the entity in place before persistence.
    Expects '_event_meta' dict with keys:
    - 'event_type': str
    - 'original_event': dict
    """
    event_meta = entity.pop('_event_meta', {})
    event_type = event_meta.get('event_type')
    event = event_meta.get('original_event', {})

    if not event_type or not isinstance(event, dict):
        logger.warning("Workflow called without valid event metadata")
        return entity

    # Add processed timestamp
    entity['processed_at'] = datetime.utcnow().isoformat() + 'Z'

    # Fetch cat fact asynchronously but tolerate failure
    cat_fact = await fetch_cat_fact()

    # Defensive fallback for timestamp
    timestamp = event.get("timestamp")
    try:
        datetime.fromisoformat(timestamp)
    except Exception:
        timestamp = datetime.utcnow().isoformat() + 'Z'

    if event_type == "created":
        # On create, fill all relevant fields explicitly
        entity.update({
            "order_id": event.get("order_id"),
            "cat_type": event.get("cat_type"),
            "quantity": event.get("quantity"),
            "price": event.get("price"),
            "status": "created",
            "last_updated": timestamp,
            "cat_fact": cat_fact,
        })
    elif event_type == "updated":
        # Update existing entity with event values if present, else keep current
        entity.update({
            "cat_type": event.get("cat_type", entity.get("cat_type")),
            "quantity": event.get("quantity", entity.get("quantity")),
            "price": event.get("price", entity.get("price")),
            "status": "updated",
            "last_updated": timestamp,
            "cat_fact": cat_fact or entity.get("cat_fact"),
        })
    elif event_type == "canceled":
        entity.update({
            "status": "canceled",
            "last_updated": timestamp,
            "cat_fact": cat_fact or entity.get("cat_fact"),
        })
    else:
        logger.warning(f"Unknown event_type in workflow: {event_type}")

    return entity

async def process_event(event: dict):
    order_id = event.get("order_id")
    event_type = event.get("event_type")
    timestamp = event.get("timestamp")

    if not order_id or not event_type or not timestamp:
        logger.warning(f"Invalid event received: missing required fields: {event}")
        return

    try:
        datetime.fromisoformat(timestamp)
    except Exception:
        logger.warning(f"Invalid timestamp format: {timestamp}")
        return

    try:
        current_order = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="order",
            entity_version=ENTITY_VERSION,
            technical_id=order_id
        )
    except Exception:
        logger.exception(f"Failed to fetch order item for order_id={order_id}")
        return

    if current_order:
        entity = dict(current_order)
    else:
        entity = {}

    # Inject event metadata for the workflow
    entity['_event_meta'] = {
        'event_type': event_type,
        'original_event': event,
    }

    try:
        entity = await process_order(entity)
    except Exception:
        logger.exception(f"Workflow processing failed for order_id={order_id}")
        return

    try:
        if current_order:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="order",
                entity_version=ENTITY_VERSION,
                entity=entity,
                technical_id=order_id,
                meta={}
            )
        else:
            # Pass workflow again for compliance; won't cause recursion as add_item workflow is async pre-persist
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="order",
                entity_version=ENTITY_VERSION,
                entity=entity
            )
        logger.info(f"Order {order_id} processed successfully with event_type={event_type}")
    except Exception:
        logger.exception(f"Failed to persist order {order_id}")

@routes_bp.route("/orders/events", methods=["POST"])
@validate_request(OrderEvent)
async def post_order_event(data: OrderEvent):
    event = data.__dict__
    try:
        asyncio.create_task(process_event(event))
    except Exception:
        logger.exception("Failed to schedule event processing task")
        return jsonify({"status": "error", "message": "Failed to start event processing"}), 500
    return jsonify({"status": "success", "message": "Event processing started", "order_id": event.get("order_id")}), 200

@routes_bp.route("/orders/<order_id>", methods=["GET"])
async def get_order(order_id: str):
    try:
        order = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="order",
            entity_version=ENTITY_VERSION,
            technical_id=order_id
        )
    except Exception:
        logger.exception(f"Failed to fetch order {order_id}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

    if not order:
        return jsonify({"status": "error", "message": "Order not found"}), 404
    return jsonify(order), 200

@routes_bp.route("/orders", methods=["GET"])
async def get_all_orders():
    try:
        all_orders = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="order",
            entity_version=ENTITY_VERSION,
        )
    except Exception:
        logger.exception("Failed to fetch all orders")
        return jsonify({"status": "error", "message": "Internal server error"}), 500
    return jsonify(all_orders), 200