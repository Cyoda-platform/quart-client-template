```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory async-safe cache for orders state
# Use asyncio.Lock to protect from concurrent mutation
orders_lock = asyncio.Lock()
orders_cache: Dict[str, dict] = {}

# Example external API usage placeholder (real API)
# We'll use a public API to simulate external call (e.g. Cat Facts API)
CAT_FACTS_API = "https://catfact.ninja/fact"

async def fetch_cat_fact() -> Optional[str]:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(CAT_FACTS_API, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            return data.get("fact")
        except Exception as e:
            logger.exception("Failed to fetch cat fact from external API")
            return None


async def process_event(event: dict):
    """
    Process a cat order event.
    Validate and update orders_cache accordingly.
    Fetch external data (cat fact) to simulate external API usage.
    """
    order_id = event.get("order_id")
    event_type = event.get("event_type")
    timestamp = event.get("timestamp")

    # Basic validations - TODO: Improve validation based on real schema if needed
    if not order_id or not event_type or not timestamp:
        logger.warning(f"Invalid event received: missing required fields: {event}")
        return

    try:
        event_time = datetime.fromisoformat(timestamp)
    except Exception:
        logger.warning(f"Invalid timestamp format: {timestamp}")
        return

    # Fetch cat fact for enrichment (simulate external data retrieval & business logic)
    cat_fact = await fetch_cat_fact()

    async with orders_lock:
        order = orders_cache.get(order_id, {})
        # Update order state based on event_type
        if event_type == "created":
            order = {
                "order_id": order_id,
                "cat_type": event.get("cat_type"),
                "quantity": event.get("quantity"),
                "price": event.get("price"),
                "status": "created",
                "last_updated": timestamp,
                "cat_fact": cat_fact,  # enrichment from external API
            }
        elif event_type == "updated":
            # Merge updates, keep previous fields if not present in event
            order.update({
                "cat_type": event.get("cat_type", order.get("cat_type")),
                "quantity": event.get("quantity", order.get("quantity")),
                "price": event.get("price", order.get("price")),
                "status": "updated",
                "last_updated": timestamp,
                "cat_fact": cat_fact or order.get("cat_fact"),
            })
        elif event_type == "canceled":
            order.update({
                "status": "canceled",
                "last_updated": timestamp,
                # Keep existing fields, no price/quantity updates on cancel
                "cat_fact": cat_fact or order.get("cat_fact"),
            })
        else:
            logger.warning(f"Unknown event_type: {event_type} for order_id: {order_id}")
            return

        orders_cache[order_id] = order
        logger.info(f"Order {order_id} processed: event_type={event_type}")

@app.route("/orders/events", methods=["POST"])
async def post_order_event():
    """
    POST /orders/events
    Accept an order event JSON, process it asynchronously, respond immediately.
    """
    try:
        event = await request.get_json()
        if not isinstance(event, dict):
            return jsonify({"status": "error", "message": "Invalid JSON body"}), 400

        # Fire and forget processing task
        asyncio.create_task(process_event(event))

        return jsonify({"status": "success", "message": "Event processing started", "order_id": event.get("order_id")}), 200
    except Exception as e:
        logger.exception("Exception in POST /orders/events")
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@app.route("/orders/<order_id>", methods=["GET"])
async def get_order(order_id: str):
    """
    GET /orders/{order_id}
    Retrieve stored order info or 404 if not found.
    """
    async with orders_lock:
        order = orders_cache.get(order_id)

    if not order:
        return jsonify({"status": "error", "message": "Order not found"}), 404

    return jsonify(order), 200


@app.route("/orders", methods=["GET"])
async def get_all_orders():
    """
    GET /orders
    Return list of all stored orders.
    """
    async with orders_lock:
        all_orders = list(orders_cache.values())

    return jsonify(all_orders), 200


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
