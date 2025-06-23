import asyncio
import logging
from datetime import datetime
from typing import Optional

import httpx
from dataclasses import dataclass
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
class SubscriptionRequest:
    email: str
    name: Optional[str] = None

@dataclass
class InteractionRequest:
    subscriberId: str
    interactionType: str
    factId: str

CAT_FACT_API_URL = "https://catfact.ninja/fact"

async def fetch_cat_fact() -> dict:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(CAT_FACT_API_URL, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.exception(f"Failed to fetch cat fact: {e}")
            raise

async def send_email(to_email: str, subject: str, body: str):
    # TODO: Implement real email service
    logger.info(f"Sending email to {to_email} with subject '{subject}' and body: {body}")

# Workflow functions

async def process_cat_fact(entity: dict) -> dict:
    """
    This workflow runs after the cat_fact entity is created.
    It sends the fact to all subscribers asynchronously.
    """
    fact_text = entity.get("fact")
    if not fact_text:
        logger.warning("Cat fact entity missing 'fact' key")
        return entity

    # Get all subscribers
    try:
        subscribers = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        logger.error(f"Failed to retrieve subscribers in cat_fact workflow: {e}")
        return entity

    # Send emails concurrently for speed
    async def send_to_sub(sub):
        try:
            await send_email(sub["email"], "Your Weekly Cat Fact 🐱", fact_text)
        except Exception as e:
            logger.error(f"Failed to send email to {sub['email']}: {e}")

    await asyncio.gather(*(send_to_sub(sub) for sub in subscribers.values()))
    return entity

async def process_subscriber(entity: dict) -> dict:
    """
    This workflow runs after subscriber creation.
    Could be used to send welcome email or initialize related data.
    """
    email = entity.get("email")
    name = entity.get("name", "")
    if email:
        try:
            await send_email(email, "Welcome to Cat Facts Newsletter",
                             f"Hello {name or 'subscriber'}, thank you for subscribing!")
        except Exception as e:
            logger.error(f"Failed to send welcome email to {email}: {e}")
    return entity

async def process_interaction(entity: dict) -> dict:
    """
    Placeholder workflow for interactions.
    Extend if you want to trigger side effects upon interaction recording.
    """
    # For now, no additional async operations needed
    return entity

# Routes

@app.route("/subscribe", methods=["POST"])
@validate_request(SubscriptionRequest)
async def subscribe(data: SubscriptionRequest):
    email = data.email
    name = data.name
    if not email:
        return jsonify({"message": "Email is required"}), 400

    # Check if email already subscribed
    try:
        subscribers = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        logger.error(f"Failed to get subscribers: {e}")
        return jsonify({"message": "Internal server error"}), 500

    for sub_id, sub in subscribers.items():
        if sub.get("email", "").lower() == email.lower():
            return jsonify({"message": "Email already subscribed", "subscriberId": sub_id}), 200

    subscriber_data = {"email": email, "name": name}
    try:
        subscriber_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
            entity=subscriber_data,
            workflow=process_subscriber
        )
    except Exception as e:
        logger.error(f"Failed to add subscriber: {e}")
        return jsonify({"message": "Internal server error"}), 500

    logger.info(f"New subscriber added: {email} (id: {subscriber_id})")
    return jsonify({"message": "Subscription successful", "subscriberId": subscriber_id}), 201


@app.route("/subscribers/count", methods=["GET"])
async def get_subscribers_count():
    try:
        subscribers = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        logger.error(f"Failed to get subscribers count: {e}")
        return jsonify({"message": "Internal server error"}), 500

    return jsonify({"count": len(subscribers)})


@app.route("/fetch-and-send-fact", methods=["POST"])
async def fetch_and_send_fact():
    requested_at = datetime.utcnow().isoformat()
    try:
        # Fetch cat fact BEFORE creating entity
        cat_fact_data = await fetch_cat_fact()
        fact_text = cat_fact_data.get("fact", "No fact retrieved")
        fact_data = {"fact": fact_text, "createdAt": datetime.utcnow().isoformat()}

        # Add cat_fact entity with workflow that sends emails to subscribers
        fact_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="cat_fact",
            entity_version=ENTITY_VERSION,
            entity=fact_data,
            workflow=process_cat_fact
        )

        return jsonify({
            "message": f"Cat fact sent to subscribers",
            "fact": fact_text,
            "factId": fact_id,
            "sentAt": requested_at
        })
    except Exception as e:
        logger.error(f"Failed to fetch and send cat fact: {e}")
        return jsonify({"message": "Failed to fetch and send cat fact"}), 500


@app.route("/interaction", methods=["POST"])
@validate_request(InteractionRequest)
async def record_interaction(data: InteractionRequest):
    subscriber_id = data.subscriberId
    interaction_type = data.interactionType
    fact_id = data.factId

    # Check subscriber exists
    try:
        subscriber = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
            technical_id=subscriber_id
        )
    except Exception as e:
        logger.error(f"Failed to get subscriber {subscriber_id}: {e}")
        return jsonify({"message": "Internal server error"}), 500

    if subscriber is None:
        return jsonify({"message": "Subscriber not found"}), 404

    # Check fact exists
    try:
        fact = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="cat_fact",
            entity_version=ENTITY_VERSION,
            technical_id=fact_id
        )
    except Exception as e:
        logger.error(f"Failed to get cat fact {fact_id}: {e}")
        return jsonify({"message": "Internal server error"}), 500

    if fact is None:
        return jsonify({"message": "Fact not found"}), 404

    if interaction_type not in ("open", "click"):
        return jsonify({"message": "Invalid interactionType"}), 400

    interaction_data = {
        "subscriberId": subscriber_id,
        "interactionType": interaction_type,
        "factId": fact_id,
        "timestamp": datetime.utcnow().isoformat()
    }

    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="interaction",
            entity_version=ENTITY_VERSION,
            entity=interaction_data,
            workflow=process_interaction
        )
    except Exception as e:
        logger.error(f"Failed to add interaction: {e}")
        return jsonify({"message": "Internal server error"}), 500

    logger.info(f"Recorded interaction: sub={subscriber_id}, type={interaction_type}, fact={fact_id}")
    return jsonify({"message": "Interaction recorded"})


@app.route("/interactions/report", methods=["GET"])
async def interactions_report():
    try:
        interactions = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="interaction",
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        logger.error(f"Failed to get interactions: {e}")
        return jsonify({"message": "Internal server error"}), 500

    total_opens = sum(1 for i in interactions.values() if i.get("interactionType") == "open")
    total_clicks = sum(1 for i in interactions.values() if i.get("interactionType") == "click")
    return jsonify({"totalOpens": total_opens, "totalClicks": total_clicks})


if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)