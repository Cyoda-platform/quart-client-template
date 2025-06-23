import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

import httpx
from quart import Blueprint, jsonify
from quart_schema import validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

@dataclass
class Subscription:
    email: str  # simple email field for subscription

ENTITY_NAME = "subscription"  # underscore lowercase
FACT_SENT_ENTITY_NAME = "fact_sent"
INTERACTION_ENTITY_NAME = "interaction"
CAT_FACT_API_URL = "https://catfact.ninja/fact"

# Dummy email sending function
async def send_email(to_email: str, subject: str, body: str):
    # TODO: Replace with real email sending implementation
    logger.info(f"Sending email to {to_email} | Subject: {subject} | Body preview: {body[:50]}...")

# Workflow function for subscription: add timestamp and send confirmation email
async def process_subscription(entity: dict):
    entity["subscribed_at"] = datetime.utcnow().isoformat()
    email = entity.get("email")
    if email:
        # Fire and forget sending confirmation email
        asyncio.create_task(send_email(
            to_email=email,
            subject="Subscription Confirmation",
            body="Thank you for subscribing!"
        ))
    return entity

# Workflow function for fact_sent: send cat fact emails to all subscribers,
# and add/update interaction entity to increment emails_sent count.
async def process_fact_sent(entity: dict):
    fact = entity.get("fact")
    if not fact:
        logger.error("process_fact_sent: no 'fact' in entity")
        return entity

    # Fetch all subscribers
    try:
        subscribers = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        logger.exception(f"process_fact_sent: error fetching subscribers: {e}")
        return entity

    # Send emails concurrently
    send_tasks = []
    subject = "Your Weekly Cat Fact "
    for subscriber in subscribers:
        email = subscriber.get("email")
        if email:
            send_tasks.append(send_email(email, subject, fact))
    if send_tasks:
        try:
            await asyncio.gather(*send_tasks)
        except Exception as e:
            logger.exception(f"process_fact_sent: error sending emails: {e}")

    sent_count = len(send_tasks)

    # Update or create interaction entity to increment emails_sent
    try:
        interactions = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=INTERACTION_ENTITY_NAME,
            entity_version=ENTITY_VERSION
        )
        if interactions:
            interaction = interactions[0]
            technical_id = str(interaction.get("id") or interaction.get("technical_id") or "")
            updated_interaction = {
                "emails_sent": interaction.get("emails_sent", 0) + sent_count,
                "opens": interaction.get("opens", 0),
                "clicks": interaction.get("clicks", 0),
            }
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model=INTERACTION_ENTITY_NAME,
                entity_version=ENTITY_VERSION,
                entity=updated_interaction,
                technical_id=technical_id,
                meta={}
            )
        else:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model=INTERACTION_ENTITY_NAME,
                entity_version=ENTITY_VERSION,
                entity={"emails_sent": sent_count, "opens": 0, "clicks": 0}
            )
    except Exception as e:
        logger.exception(f"process_fact_sent: error updating interactions: {e}")

    return entity

@routes_bp.route("/api/subscribe", methods=["POST"])
@validate_request(Subscription)
async def subscribe(data: Subscription):
    email = data.email
    if not email or "@" not in email:
        return jsonify({"success": False, "message": "Invalid email"}), 400

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
    try:
        existing_items = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            condition=condition
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"success": False, "message": "Error checking subscription"}), 500

    if existing_items:
        return jsonify({"success": False, "message": "Email already subscribed"}), 400

    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=data.__dict__
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"success": False, "message": "Error adding subscription"}), 500

    return jsonify({"success": True, "message": "Subscription successful", "id": str(id)})

@routes_bp.route("/api/facts/send-weekly", methods=["POST"])
async def send_weekly_fact():
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(CAT_FACT_API_URL, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            fact = data.get("fact")
            if not fact:
                logger.error("Cat fact API response missing 'fact'")
                return jsonify({"success": False, "message": "Failed to retrieve cat fact"}), 500
        except Exception as e:
            logger.exception(e)
            return jsonify({"success": False, "message": "Error fetching cat fact"}), 500

    # Persist fact_sent entity
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=FACT_SENT_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity={"fact": fact, "sent_at": datetime.utcnow().isoformat()}
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"success": False, "message": "Error recording/sending fact"}), 500

    return jsonify({"success": True, "message": "Weekly cat fact sent"})

@routes_bp.route("/api/report/subscribers-count", methods=["GET"])
async def subscribers_count():
    try:
        subscribers = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION
        )
        count = len(subscribers)
    except Exception as e:
        logger.exception(e)
        return jsonify({"success": False, "message": "Error fetching subscriber count"}), 500
    return jsonify({"subscribersCount": count})

@routes_bp.route("/api/report/interactions", methods=["GET"])
async def interactions():
    try:
        interactions_list = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=INTERACTION_ENTITY_NAME,
            entity_version=ENTITY_VERSION
        )
        if interactions_list:
            interaction = interactions_list[0]
            total_emails_sent = interaction.get("emails_sent", 0)
            total_opens = interaction.get("opens", 0)
            total_clicks = interaction.get("clicks", 0)
        else:
            total_emails_sent = 0
            total_opens = 0
            total_clicks = 0
    except Exception as e:
        logger.exception(e)
        return jsonify({"success": False, "message": "Error fetching interactions"}), 500

    return jsonify({
        "totalEmailsSent": total_emails_sent,
        "totalOpens": total_opens,
        "totalClicks": total_clicks,
    })