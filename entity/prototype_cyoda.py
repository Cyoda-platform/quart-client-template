import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

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
class Subscription:
    email: str  # simple email field for subscription

ENTITY_NAME = "subscription"  # entity name is underscore_lowercase

CAT_FACT_API_URL = "https://catfact.ninja/fact"

# Dummy email sending function
async def send_email(to_email: str, subject: str, body: str):
    # TODO: Replace with real email sending implementation
    logger.info(f"Sending email to {to_email} | Subject: {subject} | Body preview: {body[:50]}...")

@app.route("/api/subscribe", methods=["POST"])
@validate_request(Subscription)  # workaround: validate_request last for POST requests due to library defect
async def subscribe(data: Subscription):
    email = data.email
    if "@" not in email:
        return jsonify({"success": False, "message": "Invalid email"}), 400

    # Check if email already subscribed - by condition search
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

@app.route("/api/facts/send-weekly", methods=["POST"])
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

    # Fetch all subscribers
    try:
        subscribers = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"success": False, "message": "Error fetching subscribers"}), 500

    send_tasks = []
    subject = "Your Weekly Cat Fact 🐱"
    for subscriber in subscribers:
        email = subscriber.get("email")
        if email:
            send_tasks.append(send_email(email, subject, fact))
    await asyncio.gather(*send_tasks)
    sent_count = len(send_tasks)

    # Record fact sent - use entity 'fact_sent' entity
    FACT_SENT_ENTITY_NAME = "fact_sent"
    now = datetime.utcnow().isoformat()

    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=FACT_SENT_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity={"fact": fact, "sent_at": now}
        )
    except Exception as e:
        logger.exception(e)
        # do not fail entire request if recording fact fails

    # Increment interactions - use 'interaction' entity with a single record or store in some way
    # Here we simulate increment by retrieving, incrementing, and updating or adding record
    INTERACTION_ENTITY_NAME = "interaction"

    try:
        interactions = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=INTERACTION_ENTITY_NAME,
            entity_version=ENTITY_VERSION
        )
        if interactions:
            interaction = interactions[0]
            technical_id = str(interaction.get("id") or interaction.get("technical_id") or "")
            emails_sent = interaction.get("emails_sent", 0) + sent_count
            opens = interaction.get("opens", 0)
            clicks = interaction.get("clicks", 0)
            updated_interaction = {
                "emails_sent": emails_sent,
                "opens": opens,
                "clicks": clicks
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
            # create new
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model=INTERACTION_ENTITY_NAME,
                entity_version=ENTITY_VERSION,
                entity={"emails_sent": sent_count, "opens": 0, "clicks": 0}
            )
    except Exception as e:
        logger.exception(e)
        # do not fail entire request if interaction update fails

    return jsonify({"success": True, "sentTo": sent_count, "fact": fact})

@app.route("/api/report/subscribers-count", methods=["GET"])
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

@app.route("/api/report/interactions", methods=["GET"])
async def interactions():
    INTERACTION_ENTITY_NAME = "interaction"
    try:
        interactions = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=INTERACTION_ENTITY_NAME,
            entity_version=ENTITY_VERSION
        )
        if interactions:
            interaction = interactions[0]
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

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)