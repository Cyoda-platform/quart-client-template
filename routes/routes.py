import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict

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
class Subscriber:
    email: str

@dataclass
class SendRequest:
    pass  # Empty dataclass for POST body; TODO: add fields if control params are needed

entity_name = "subscriber"  # underscore lowercase entity name

# In-memory async-safe caches for latest fact and report only
class Cache:
    def __init__(self):
        self._latest_fact: Dict = {}
        self._report = {
            "subscriberCount": 0,
            "factsSent": 0,
            "lastSentAt": None,
        }
        self._lock = asyncio.Lock()

    async def update_latest_fact(self, fact: str):
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            self._latest_fact = {"catFact": fact, "sentAt": now}
            self._report["factsSent"] += 1
            self._report["lastSentAt"] = now

    async def get_latest_fact(self) -> Dict:
        async with self._lock:
            return dict(self._latest_fact)

    async def get_report(self) -> Dict:
        async with self._lock:
            return dict(self._report)

    async def update_subscriber_count(self, count: int):
        async with self._lock:
            self._report["subscriberCount"] = count

cache = Cache()

async def send_email(to_email: str, cat_fact: str):
    # Simulate sending email asynchronously, handle errors silently to not interrupt flow
    try:
        await asyncio.sleep(0.1)
        logger.info(f"Sent cat fact email to {to_email}")
        # TODO: Integrate with real email service provider
    except Exception as e:
        logger.error(f"Error sending email to {to_email}: {e}")

async def fetch_cat_fact() -> str:
    url = "https://catfact.ninja/fact"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            fact = data.get("fact")
            if not fact:
                raise ValueError("No 'fact' field in response from Cat Fact API")
            return fact
    except Exception as e:
        logger.error(f"Failed to fetch cat fact: {e}")
        raise

# Workflow function applied to the entity asynchronously before persistence.
# This function takes the entity data as the only argument.
# You can change entity state inside this function.
async def process_subscriber(entity_data: dict):
    # Add subscribedAt timestamp if not present
    if 'subscribedAt' not in entity_data:
        entity_data['subscribedAt'] = datetime.now(timezone.utc).isoformat()

    # Fetch a cat fact
    try:
        cat_fact = await fetch_cat_fact()
    except Exception:
        cat_fact = None

    if cat_fact:
        # Send a cat fact email to this subscriber
        await send_email(entity_data['email'], cat_fact)

        # Update latest fact and report caches
        try:
            await cache.update_latest_fact(cat_fact)
        except Exception as e:
            logger.error(f"Failed to update latest fact and report cache: {e}")

    # Update subscriber count cache by querying current count asynchronously
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION
        )
        await cache.update_subscriber_count(len(items))
    except Exception as e:
        logger.error(f"Failed to update subscriber count in cache: {e}")

@app.route("/api/subscribers", methods=["POST"])
@validate_request(Subscriber)  # Workaround: place validate_request last for POST due to quart-schema defect
async def subscribe(data: Subscriber):
    email = data.email.strip().lower()
    if not email or "@" not in email:
        return jsonify({"error": "Invalid or missing email"}), 400

    # Check if subscriber exists by condition
    condition = {
        "cyoda": {
            "type": "group",
            "operator": "AND",
            "conditions": [
                {
                    "jsonPath": "$.email",
                    "operatorType": "EQUALS",
                    "value": email,
                    "type": "simple"
                }
            ]
        }
    }
    try:
        existing_subs = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            condition=condition
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to check existing subscribers"}), 500

    if existing_subs:
        return jsonify({"error": "Email already subscribed"}), 400

    data_dict = {"email": email}
    try:
        new_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=data_dict
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add subscriber"}), 500

    logger.info(f"New subscriber added: {email} with id {new_id}")
    return jsonify({"id": str(new_id)}), 201

@app.route("/api/subscribers", methods=["GET"])
async def list_subscribers():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve subscribers"}), 500

    subs = [{"email": item.get("email")} for item in items if "email" in item]
    return jsonify({"subscribers": subs, "count": len(subs)}), 200

@app.route("/api/catfact/send", methods=["POST"])
@validate_request(SendRequest)  # Workaround: place validate_request last for POST due to quart-schema defect
async def send_cat_fact(data: SendRequest):
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve subscribers"}), 500

    subscribers = [item.get("email") for item in items if "email" in item]
    if not subscribers:
        return jsonify({"error": "No subscribers to send emails to"}), 400

    try:
        cat_fact = await fetch_cat_fact()
    except Exception:
        return jsonify({"error": "Failed to fetch cat fact"}), 500

    # Send emails concurrently, but protect against exceptions stopping others
    async def safe_send(email):
        try:
            await send_email(email, cat_fact)
        except Exception as e:
            logger.error(f"Failed to send cat fact email to {email}: {e}")

    await asyncio.gather(*(safe_send(email) for email in subscribers))

    # Update latest fact and report caches atomically
    try:
        await cache.update_latest_fact(cat_fact)
    except Exception as e:
        logger.error(f"Failed to update latest fact and report cache: {e}")

    # Update subscriber count cache
    try:
        await cache.update_subscriber_count(len(subscribers))
    except Exception as e:
        logger.error(f"Failed to update subscriber count in cache: {e}")

    logger.info(f"Cat fact sent to {len(subscribers)} subscribers")

    return jsonify({"catFact": cat_fact, "emailsSent": len(subscribers)}), 200

@app.route("/api/catfact/latest", methods=["GET"])
async def get_latest_cat_fact():
    latest = await cache.get_latest_fact()
    if not latest:
        return jsonify({"error": "No cat fact sent yet"}), 404
    return jsonify(latest), 200

@app.route("/api/report", methods=["GET"])
async def get_report():
    report = await cache.get_report()
    return jsonify(report), 200

if __name__ == '__main__':
    import sys

    logging.basicConfig(
        format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        level=logging.INFO,
        stream=sys.stdout,
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)