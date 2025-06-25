from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional
from uuid import uuid4

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

@dataclass
class SubscribeRequest:
    email: str
    name: Optional[str] = None

# Workaround for validate_request defect: @app.route first, then @validate_request last for POST
@app.route("/subscribe", methods=["POST"])
@validate_request(SubscribeRequest)
async def subscribe(data: SubscribeRequest):
    email = data.email
    name = data.name

    if not email:
        return jsonify({"error": "Email is required"}), 400

    # Use entity_service.get_items_by_condition to check if email already subscribed
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
    existing_subscribers = await entity_service.get_items_by_condition(
        token=cyoda_auth_service,
        entity_model="subscribe_request",
        entity_version=ENTITY_VERSION,
        condition=condition
    )
    if existing_subscribers:
        return jsonify({"error": "Email already subscribed"}), 400

    # Prepare data dict
    data_dict = {
        "email": email,
        "name": name,
        "subscribedAt": datetime.utcnow().isoformat(),
    }
    try:
        new_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="subscribe_request",
            entity_version=ENTITY_VERSION,
            entity=data_dict
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add subscriber"}), 500

    logger.info(f"New subscriber: {email} (id={new_id})")
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
    fact = await fetch_cat_fact()
    if not fact:
        return jsonify({"error": "Failed to fetch cat fact"}), 500

    emails_sent = 0

    try:
        subscribers = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="subscribe_request",
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve subscribers"}), 500

    if not subscribers:
        return jsonify({"message": "No subscribers to send to", "fact": fact, "emailsSent": 0})

    async def send_to_subscriber(sub):
        nonlocal emails_sent
        subject = "Your Weekly Cat Fact! 🐱"
        name_part = f" {sub.get('name')}" if sub.get('name') else ""
        body = f"Hello{name_part},\n\nHere's your cat fact this week:\n\n{fact}\n\nEnjoy!"
        try:
            sent = await send_email(sub["email"], subject, body)
            if sent:
                emails_sent += 1
        except Exception as e:
            logger.exception(f"Failed to send email to {sub['email']}: {e}")

    tasks = [send_to_subscriber(sub) for sub in subscribers]
    await asyncio.gather(*tasks)

    # interaction_metrics no longer in-memory; simulate counts here or skip
    logger.info(f"Sent cat fact to {emails_sent} subscribers")
    return jsonify({"message": "Cat fact fetched and emails sent", "fact": fact, "emailsSent": emails_sent})

@app.route("/report/interactions", methods=["GET"])
async def get_interactions_report():
    # Since interaction_metrics was in-memory, and no external service is defined for it,
    # return mocked or static values
    interaction_metrics = {
        "emailsSent": 0,
        "emailsOpened": 0,
        "clicks": 0,
    }
    return jsonify(interaction_metrics)

# Simulate email sending - TODO: replace with real Email Service integration
async def send_email(to_email: str, subject: str, body: str) -> bool:
    logger.info(f"Sending email to {to_email} with subject '{subject}'")
    await asyncio.sleep(0.1)  # simulate network latency
    return True

# Fetch a random cat fact from the external Cat Fact API
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