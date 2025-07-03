from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime, timezone
import uuid

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
import httpx

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
class SignupRequest:
    email: str
    name: str = None

@dataclass
class SubscriberQuery:
    countOnly: bool = False

# Workflow function for subscriber entity
async def process_subscriber(entity: dict) -> dict:
    """
    Workflow function applied to subscriber entity before persistence.
    - Adds createdAt timestamp
    - Sends welcome email asynchronously (fire-and-forget)
    """
    if "createdAt" not in entity:
        entity["createdAt"] = datetime.now(timezone.utc).isoformat()

    async def send_welcome_email():
        try:
            await asyncio.sleep(0.05)  # Simulate sending email
            logger.info(f"Welcome email sent to {entity.get('email')}")
        except Exception:
            logger.exception("Failed to send welcome email")

    # Fire and forget sending welcome email
    asyncio.create_task(send_welcome_email())

    return entity

# Workflow function for fact entity
async def process_fact(entity: dict) -> dict:
    """
    Workflow function applied to fact entity before persistence.
    - Fetches a cat fact if 'fact' not provided
    - Adds sentDate timestamp if missing
    - Sends fact email to all subscribers asynchronously
    - Updates emailsSent count on the fact entity before persisting
    """
    if not entity.get("fact"):
        url = "https://catfact.ninja/fact"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                entity["fact"] = data.get("fact", "Cats are mysterious creatures!")
        except Exception:
            logger.exception("Failed to fetch cat fact")
            entity["fact"] = "Cats are mysterious creatures!"

    if "sentDate" not in entity:
        entity["sentDate"] = datetime.now(timezone.utc).isoformat()

    # Initialize counts if missing
    entity.setdefault("emailsSent", 0)
    entity.setdefault("emailsOpened", 0)
    entity.setdefault("linksClicked", 0)

    try:
        subscribers = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
        )
    except Exception:
        logger.exception("Failed to retrieve subscribers")
        subscribers = []

    async def send_email(email: str, fact_text: str):
        try:
            await asyncio.sleep(0.05)  # Simulate sending email
            logger.info(f"Sent cat fact email to {email}")
        except Exception:
            logger.exception(f"Failed to send cat fact email to {email}")

    send_tasks = []
    for sub in subscribers:
        email = sub.get("email")
        if email:
            send_tasks.append(send_email(email, entity["fact"]))

    if send_tasks:
        await asyncio.gather(*send_tasks)

    entity["emailsSent"] = len(send_tasks)

    return entity

@app.route("/api/signup", methods=["POST"])
@validate_request(SignupRequest)
async def signup(data: SignupRequest):
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
        existing_subscribers = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
            condition=condition
        )
    except Exception:
        logger.exception("Failed to check existing subscriber")
        return jsonify({"error": "Internal server error"}), 500

    if existing_subscribers:
        return jsonify({"message": "Email already subscribed"}), 409

    subscriber_data = {"email": email, "name": data.name}
    try:
        subscriber_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
            entity=subscriber_data,
            workflow=process_subscriber
        )
    except Exception:
        logger.exception("Failed to add subscriber")
        return jsonify({"error": "Failed to subscribe"}), 500

    logger.info(f"New subscriber added: {email}")
    return jsonify({"message": "Subscription successful", "subscriberId": subscriber_id})

@validate_querystring(SubscriberQuery)
@app.route("/api/subscribers", methods=["GET"])
async def get_subscribers():
    args = SubscriberQuery(**request.args)
    try:
        subscribers_raw = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
        )
    except Exception:
        logger.exception("Failed to retrieve subscribers")
        return jsonify({"error": "Failed to retrieve subscribers"}), 500

    if args.countOnly:
        return jsonify({"totalSubscribers": len(subscribers_raw)})

    subs_list = [
        {"id": str(sub.get("id", "")), "email": sub.get("email"), "name": sub.get("name")}
        for sub in subscribers_raw
    ]
    return jsonify({"totalSubscribers": len(subscribers_raw), "subscribers": subs_list})

@app.route("/api/facts/sendWeekly", methods=["POST"])
async def send_weekly_fact():
    fact_data = {}
    try:
        fact_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="fact",
            entity_version=ENTITY_VERSION,
            entity=fact_data,
            workflow=process_fact
        )
    except Exception:
        logger.exception("Failed to send weekly cat fact")
        return jsonify({"error": "Failed to send cat fact"}), 500

    return jsonify({
        "message": "Cat fact sent to subscribers",
        "factId": fact_id
    })

@app.route("/api/facts/reports", methods=["GET"])
async def get_facts_reports():
    try:
        facts_raw = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="fact",
            entity_version=ENTITY_VERSION,
        )
    except Exception:
        logger.exception("Failed to retrieve facts reports")
        return jsonify({"error": "Failed to retrieve facts"}), 500

    facts_list = []
    for fact in facts_raw:
        facts_list.append({
            "factId": str(fact.get("id", "")),
            "fact": fact.get("fact"),
            "sentDate": fact.get("sentDate"),
            "emailsSent": fact.get("emailsSent"),
            "emailsOpened": fact.get("emailsOpened"),
            "linksClicked": fact.get("linksClicked")
        })
    return jsonify({"facts": facts_list})

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)