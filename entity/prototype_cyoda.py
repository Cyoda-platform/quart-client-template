import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

entity_name = "subscriber"  # underscore lowercase entity name

# Request schemas
@dataclass
class SubscribeRequest:
    email: str
    name: Optional[str] = None

@dataclass
class UnsubscribeRequest:
    email: str

async def fetch_cat_fact() -> Optional[str]:
    url = "https://catfact.ninja/fact"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            fact = data.get("fact")
            if not fact:
                logger.warning("Cat fact API returned no fact")
                return None
            return fact
        except Exception:
            logger.exception("Failed to fetch cat fact")
            return None

async def send_email_stub(email: str, subject: str, body: str) -> bool:
    # TODO: Replace this stub with real email sending logic (SMTP / API)
    logger.info(f"Sending email to {email} with subject '{subject}' and body:\n{body}")
    await asyncio.sleep(0.05)
    return True

@app.route("/subscribe", methods=["POST"])
@validate_request(SubscribeRequest)
async def subscribe(data: SubscribeRequest):
    email = data.email.strip().lower()
    name = data.name
    if "@" not in email or "." not in email:
        return jsonify(status="error", message="Invalid email format"), 400

    # Prepare data object for entity_service
    entity_data = {"email": email, "name": name}

    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=entity_data
        )
    except Exception as e:
        logger.exception(e)
        return jsonify(status="error", message="Failed to subscribe"), 500

    return jsonify(status="success", id=str(id), message="Subscription started")

@app.route("/unsubscribe", methods=["POST"])
@validate_request(UnsubscribeRequest)
async def unsubscribe(data: UnsubscribeRequest):
    email = data.email.strip().lower()

    # We need to find the technical_id for the subscriber with this email
    # Since we cannot access in-memory, use get_items_by_condition
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
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        if not items:
            return jsonify(status="error", message="Email not found"), 400
        # Assume first match is the subscriber
        subscriber = items[0]
        technical_id = str(subscriber.get("technical_id") or subscriber.get("id") or "")
        if not technical_id:
            return jsonify(status="error", message="Invalid subscriber id"), 400

        await entity_service.delete_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            technical_id=technical_id,
            meta={}
        )
    except Exception as e:
        logger.exception(e)
        return jsonify(status="error", message="Failed to unsubscribe"), 500

    return jsonify(status="success", message="Unsubscribed successfully")

async def get_all_subscribers():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
        )
        return items
    except Exception as e:
        logger.exception(e)
        return []

@app.route("/send-weekly-fact", methods=["POST"])
async def send_weekly_fact():
    asyncio.create_task(process_send_weekly_fact())
    return jsonify(status="success", message="Weekly cat fact sending started")

async def process_send_weekly_fact():
    subscribers = await get_all_subscribers()
    if not subscribers:
        logger.info("No subscribers to send cat fact to")
        return 0

    fact = await fetch_cat_fact()
    if not fact:
        logger.warning("No cat fact retrieved, abort sending")
        return 0

    subject = "Your Weekly Cat Fact 🐱"
    body = f"Hello,\n\nHere's your weekly cat fact:\n\n{fact}\n\nEnjoy your week!"

    success_count = 0
    semaphore = asyncio.Semaphore(20)

    async def send(email: str):
        async with semaphore:
            try:
                return await send_email_stub(email, subject, body)
            except Exception:
                logger.exception(f"Failed to send email to {email}")
                return False

    tasks = [send(sub.get("email")) for sub in subscribers if sub.get("email")]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for r in results:
        if r is True:
            success_count += 1

    # We cannot track emails sent in entity_service, so skip increment logic or log only
    logger.info(f"Sent cat fact email to {success_count} subscribers")
    return success_count

@app.route("/report/subscribers", methods=["GET"])
async def report_subscribers():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
        )
        total = len(items)
    except Exception as e:
        logger.exception(e)
        total = 0
    return jsonify(total_subscribers=total)

@app.route("/report/emails-sent", methods=["GET"])
async def report_emails_sent():
    # Since emails sent counter was in-memory, and no external method provided,
    # we cannot provide this data anymore
    # Return a fixed value or a message
    return jsonify(total_emails_sent="Not available")

if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
        level=logging.INFO,
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)