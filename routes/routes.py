from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

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
class SubscribeRequest:
    email: str
    name: Optional[str] = None

# Workflow for subscribe_request entity
async def process_subscribe_request(entity: dict) -> dict:
    """
    Workflow function applied asynchronously before persisting a subscribe_request entity.
    Moves duplicate email check here, sets subscribedAt timestamp.
    """
    email = entity.get("email")
    if not email:
        raise ValueError("Email is required in subscribe_request entity")

    # Check if email already subscribed
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
    existing = await entity_service.get_items_by_condition(
        token=cyoda_auth_service,
        entity_model="subscribe_request",
        entity_version=ENTITY_VERSION,
        condition=condition
    )
    if existing:
        raise ValueError(f"Email {email} already subscribed")

    # Set subscribedAt if not already set
    if "subscribedAt" not in entity:
        entity["subscribedAt"] = datetime.utcnow().isoformat()

    return entity

# Workflow for catfact_send_job entity
async def process_catfact_send_job(entity: dict) -> dict:
    """
    Workflow function that fetches cat fact, sends emails to subscribers asynchronously.
    It does not modify the job entity but triggers side effects.
    """
    logger.info("Starting catfact_send_job workflow")

    # Fetch cat fact
    fact = await fetch_cat_fact()
    if not fact:
        logger.error("Failed to fetch cat fact in workflow")
        return entity

    # Retrieve all subscribers
    subscribers = await entity_service.get_items(
        token=cyoda_auth_service,
        entity_model="subscribe_request",
        entity_version=ENTITY_VERSION
    )
    if not subscribers:
        logger.info("No subscribers found in catfact_send_job workflow")
        return entity

    emails_sent = 0

    async def send_to_subscriber(sub):
        nonlocal emails_sent
        subject = "Your Weekly Cat Fact! 431"
        name_part = f" {sub.get('name')}" if sub.get('name') else ""
        body = f"Hello{name_part},\n\nHere's your cat fact this week:\n\n{fact}\n\nEnjoy!"
        try:
            sent = await send_email(sub["email"], subject, body)
            if sent:
                emails_sent += 1
        except Exception as e:
            logger.exception(f"Failed to send email to {sub['email']}: {e}")

    await asyncio.gather(*(send_to_subscriber(sub) for sub in subscribers))

    logger.info(f"Cat fact sent to {emails_sent} subscribers")

    # Add an entity to record the send job result
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="catfact_send_result",
            entity_version=ENTITY_VERSION,
            entity={
                "jobId": entity.get("id", str(uuid4())),
                "sentAt": datetime.utcnow().isoformat(),
                "emailsSentCount": emails_sent,
                "fact": fact
            },
            workflow=None
        )
    except Exception as e:
        logger.exception(f"Failed to record catfact_send_result: {e}")

    return entity

@app.route("/subscribe", methods=["POST"])
@validate_request(SubscribeRequest)
async def subscribe(data: SubscribeRequest):
    data_dict = {
        "email": data.email,
        "name": data.name,
    }
    try:
        new_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="subscribe_request",
            entity_version=ENTITY_VERSION,
            entity=data_dict
        )
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add subscriber"}), 500

    logger.info(f"New subscriber: {data.email} (id={new_id})")
    return jsonify({"message": "Subscription successful", "subscriberId": new_id})

@app.route("/subscribers/count", methods=["GET"])
async def get_subscriber_count():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="subscribe_request",
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve subscribers"}), 500
    count = len(items) if items else 0
    return jsonify({"subscriberCount": count})

@app.route("/fetch-and-send-catfact", methods=["POST"])
async def fetch_and_send_catfact():
    try:
        job_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="catfact_send_job",
            entity_version=ENTITY_VERSION,
            entity={}
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to start cat fact send job"}), 500

    return jsonify({"message": "Cat fact send job started", "jobId": job_id})

@app.route("/report/interactions", methods=["GET"])
async def get_interactions_report():
    try:
        results = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="catfact_send_result",
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve interaction report"}), 500

    emails_sent = sum(r.get("emailsSentCount", 0) for r in results) if results else 0

    interaction_metrics = {
        "emailsSent": emails_sent,
        "emailsOpened": 0,
        "clicks": 0,
    }
    return jsonify(interaction_metrics)

async def send_email(to_email: str, subject: str, body: str) -> bool:
    logger.info(f"Sending email to {to_email} with subject '{subject}'")
    await asyncio.sleep(0.1)
    return True

async def fetch_cat_fact() -> Optional[str]:
    url = "https://catfact.ninja/fact"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            fact = data.get("fact")
            logger.info(f"Fetched cat fact: {fact}")
            return fact
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.exception(f"Failed to fetch cat fact: {e}")
            return None

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)