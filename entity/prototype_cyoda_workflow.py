import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any
from dataclasses import dataclass

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

interaction_metrics = {
    "totalEmailsSent": 0,
    "totalClicks": 0,  # TODO: Implement tracking clicks from emails (placeholder)
    "totalOpens": 0,   # TODO: Implement tracking email opens (placeholder)
}

CAT_FACT_API_URL = "https://catfact.ninja/fact"

async def send_email(email: str, subject: str, body: str) -> None:
    # TODO: Replace with real email sending implementation
    logger.info(f"Sending email to {email} with subject '{subject}' and body: {body}")
    await asyncio.sleep(0.1)

async def process_subscriber(entity: Dict[str, Any]) -> Dict[str, Any]:
    email = entity.get("email")
    if email:
        normalized_email = email.lower()
        entity["email"] = normalized_email

        async def _send_welcome_email():
            try:
                await send_email(
                    normalized_email,
                    subject="Welcome to Cat Facts!",
                    body="Thank you for subscribing to Cat Facts!"
                )
                logger.info(f"Welcome email sent to {normalized_email}")
            except Exception as e:
                logger.exception(f"Failed to send welcome email to {normalized_email}: {e}")

        asyncio.create_task(_send_welcome_email())

    if "subscribedAt" not in entity:
        entity["subscribedAt"] = datetime.utcnow().isoformat()

    return entity

async def process_cat_fact_sent(entity: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(CAT_FACT_API_URL, timeout=10)
            response.raise_for_status()
            cat_fact_data = response.json()
            fact_text = cat_fact_data.get("fact", "Cats are mysterious creatures.")
        except Exception:
            logger.exception("Failed to fetch cat fact from external API")
            fact_text = "Cats are mysterious creatures."

    entity["factText"] = fact_text
    entity["sentAt"] = datetime.utcnow().isoformat()
    entity["emailsSent"] = 0

    try:
        subscribers = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
        )
    except Exception:
        logger.exception("Failed to get subscribers inside cat_fact_sent workflow")
        subscribers = []

    send_tasks = []
    for sub in subscribers:
        email = sub.get("email")
        if email:
            send_tasks.append(send_email(
                email,
                subject="Your Weekly Cat Fact 🐱",
                body=fact_text,
            ))

    send_results = await asyncio.gather(*send_tasks, return_exceptions=True)
    success_count = sum(1 for r in send_results if not isinstance(r, Exception))
    entity["emailsSent"] = success_count

    interaction_metrics["totalEmailsSent"] += success_count

    cat_fact_log_entity = {
        "factText": fact_text,
        "sentAt": entity["sentAt"],
        "emailsSent": success_count,
        "factId": str(uuid.uuid4()),
    }
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="cat_fact_log",
            entity_version=ENTITY_VERSION,
            entity=cat_fact_log_entity,
            workflow=None,
        )
    except Exception:
        logger.exception("Failed to add cat_fact_log entity in cat_fact_sent workflow")

    logger.info(f"Cat fact sent to {success_count} subscribers with fact: {fact_text}")

    return entity

@app.route("/subscribe", methods=["POST"])
@validate_request(SubscribeRequest)
async def subscribe(data: SubscribeRequest):
    email = data.email
    if not email:
        return jsonify({"error": "Email is required"}), 400

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
        items = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
            condition=condition,
        )
    except Exception:
        logger.exception("Failed to check existing subscriber")
        return jsonify({"error": "Failed to check existing subscriber"}), 500

    if items:
        existing_id = items[0].get("id")
        return jsonify({"message": "Email already subscribed", "subscriberId": existing_id}), 200

    data_dict = {"email": email}
    try:
        new_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
            entity=data_dict,
            workflow=process_subscriber,
        )
    except Exception:
        logger.exception("Failed to add subscriber")
        return jsonify({"error": "Failed to add subscriber"}), 500

    logger.info(f"New subscriber added: {email} with id {new_id}")
    return jsonify({"message": "Subscription successful", "subscriberId": new_id}), 201

@app.route("/subscribers/count", methods=["GET"])
async def subscribers_count():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
        )
        count = len(items)
    except Exception:
        logger.exception("Failed to retrieve subscribers count")
        return jsonify({"error": "Failed to retrieve subscribers count"}), 500
    return jsonify({"count": count})

@app.route("/facts/ingest-and-send", methods=["POST"])
async def ingest_and_send():
    try:
        new_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="cat_fact_sent",
            entity_version=ENTITY_VERSION,
            entity={},
            workflow=process_cat_fact_sent,
        )
    except Exception:
        logger.exception("Failed to ingest and send cat fact")
        return jsonify({"error": "Failed to ingest and send cat fact"}), 500

    return jsonify({"message": "Cat fact ingested and sent", "catFactSentId": new_id})

@app.route("/reports/interactions", methods=["GET"])
async def reports_interactions():
    return jsonify(interaction_metrics)

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        level=logging.INFO,
    )

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)