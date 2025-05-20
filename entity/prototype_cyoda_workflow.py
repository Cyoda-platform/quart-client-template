import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request
import httpx
from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class SubscribeRequest:
    email: str

@dataclass
class EmptyRequest:
    pass

from app_init.app_init import BeanFactory
factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

ENTITY_SUBSCRIBER = "subscriber"
ENTITY_CATFACT_REQUEST = "catfact_request"
ENTITY_LAST_CAT_FACT = "last_cat_fact"

_stats_lock = asyncio.Lock()
_email_stats = {
    "emailsSent": 0,
    "emailsOpened": 0,
    "clicks": 0,
}

async def process_subscriber(entity: dict) -> dict:
    # Add subscribedAt timestamp if missing
    entity.setdefault("subscribedAt", datetime.utcnow().isoformat())
    return entity

async def process_catfact_request(entity: dict) -> dict:
    CAT_FACT_API = "https://catfact.ninja/fact"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(CAT_FACT_API, timeout=10)
            resp.raise_for_status()
            fact_data = resp.json()
            fact = fact_data.get("fact")
            if not fact:
                logger.warning("No fact in API response")
                entity["status"] = "failed"
                entity["error"] = "No fact in API response"
                return entity
        except httpx.HTTPError as e:
            logger.exception(e)
            entity["status"] = "failed"
            entity["error"] = str(e)
            return entity

    last_fact_entity = {
        "fact": fact,
        "fetchedAt": datetime.utcnow().isoformat(),
    }
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_LAST_CAT_FACT,
            entity_version=ENTITY_VERSION,
            entity=last_fact_entity,
            workflow=None,
        )
    except Exception as e:
        logger.warning(f"Failed to store last_cat_fact entity: {e}")

    try:
        subscribers = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_SUBSCRIBER,
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.error(f"Failed to fetch subscribers: {e}")
        entity["status"] = "failed"
        entity["error"] = "Failed to fetch subscribers"
        return entity

    recipients = [s.get("email") for s in subscribers if s.get("email")]
    if not recipients:
        logger.info("No subscribers to send emails to")
        entity["status"] = "no_subscribers"
        return entity

    try:
        await _send_cat_fact_emails(recipients, fact)
    except Exception as e:
        logger.error(f"Failed to send emails: {e}")
        entity["status"] = "failed"
        entity["error"] = "Failed to send emails"
        return entity

    async with _stats_lock:
        _email_stats["emailsSent"] += len(recipients)

    entity["status"] = "completed"
    entity["recipientsCount"] = len(recipients)
    entity["fact"] = fact
    entity["completedAt"] = datetime.utcnow().isoformat()
    return entity

async def _send_cat_fact_emails(recipients: List[str], fact: str):
    logger.info(f"Sending cat fact to {len(recipients)} subscribers")
    await asyncio.sleep(0.5)  # simulate sending delay
    logger.info("Emails sent successfully")

@app.route("/api/subscribe", methods=["POST"])
@validate_request(SubscribeRequest)
async def subscribe(data: SubscribeRequest):
    entity_data = {"email": data.email}
    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_SUBSCRIBER,
            entity_version=ENTITY_VERSION,
            entity=entity_data,
            workflow=process_subscriber
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add subscriber"}), 500
    subscriber_id = str(uuid.uuid4())
    return jsonify({"message": "Subscription successful", "subscriberId": subscriber_id, "entityId": id})

@app.route("/api/fetch-and-send", methods=["POST"])
@validate_request(EmptyRequest)
async def fetch_and_send(data: EmptyRequest):
    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_CATFACT_REQUEST,
            entity_version=ENTITY_VERSION,
            entity={},
            workflow=process_catfact_request,
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to initiate cat fact sending"}), 500
    return jsonify({"message": "Cat fact request submitted", "entityId": id})

@app.route("/api/reporting/summary", methods=["GET"])
async def reporting_summary():
    try:
        subscribers = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_SUBSCRIBER,
            entity_version=ENTITY_VERSION,
        )
        total_subscribers = len(subscribers)
    except Exception as e:
        logger.exception(e)
        total_subscribers = 0

    async with _stats_lock:
        emails_sent = _email_stats["emailsSent"]
        emails_opened = _email_stats["emailsOpened"]
        clicks = _email_stats["clicks"]

    return jsonify({
        "totalSubscribers": total_subscribers,
        "emailsSent": emails_sent,
        "emailsOpened": emails_opened,
        "clicks": clicks,
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)