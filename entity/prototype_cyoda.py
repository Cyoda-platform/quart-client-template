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

async def fetch_cat_fact() -> dict:
    url = "https://catfact.ninja/fact"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.exception("Failed to fetch cat fact")
            raise e

async def send_email_stub(email: str, fact: str):
    logger.info(f"Sending email to {email} with cat fact: {fact}")
    await asyncio.sleep(0.05)

async def process_weekly_fact_send():
    try:
        cat_fact_data = await fetch_cat_fact()
        fact_text = cat_fact_data.get("fact", "Cats are mysterious creatures!")
        fact_id = str(uuid.uuid4())
        sent_date = datetime.now(timezone.utc).isoformat()

        # Store fact via entity_service
        fact_data = {
            "fact": fact_text,
            "sentDate": sent_date,
            "emailsSent": 0,
            "emailsOpened": 0,
            "linksClicked": 0
        }
        # Add fact to entity_service, id returned but we keep our own fact_id for correlation
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="fact",
            entity_version=ENTITY_VERSION,
            entity=fact_data,
            technical_id=fact_id,
            meta={}
        )

        # Retrieve current subscribers from entity_service
        subscribers_raw = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
        )
        subscribers_cache = {sub["id"]: sub for sub in subscribers_raw}

        send_tasks = []
        for subscriber in subscribers_cache.values():
            send_tasks.append(send_email_stub(subscriber["email"], fact_text))
        await asyncio.gather(*send_tasks)

        # Update emailsSent count after sending
        fact_data["emailsSent"] = len(subscribers_cache)
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="fact",
            entity_version=ENTITY_VERSION,
            entity=fact_data,
            technical_id=fact_id,
            meta={}
        )

        return fact_id, fact_text
    except Exception as e:
        logger.exception("Error processing weekly fact send")
        raise e

@app.route("/api/signup", methods=["POST"])
@validate_request(SignupRequest)  # validation last for POST (workaround for library issue)
async def signup(data: SignupRequest):
    email = data.email
    if not email:
        return jsonify({"error": "Email is required"}), 400

    # Check if email already exists
    # Use get_items_by_condition to find email
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
        entity_model="subscriber",
        entity_version=ENTITY_VERSION,
        condition=condition
    )
    if existing_subscribers:
        return jsonify({"message": "Email already subscribed"}), 409

    # Add new subscriber
    subscriber_data = {"email": email, "name": data.name}
    try:
        subscriber_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
            entity=subscriber_data
        )
    except Exception as e:
        logger.exception("Failed to add subscriber")
        return jsonify({"error": "Failed to subscribe"}), 500
    logger.info(f"New subscriber added: {email}")
    return jsonify({"message": "Subscription successful", "subscriberId": subscriber_id})

@validate_querystring(SubscriberQuery)  # validation first for GET (workaround for library issue)
@app.route("/api/subscribers", methods=["GET"])
async def get_subscribers():
    args = SubscriberQuery(**request.args)
    try:
        subscribers_raw = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
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
    try:
        fact_id, fact_text = await process_weekly_fact_send()
        return jsonify({
            "message": "Cat fact sent to subscribers",
            "factId": fact_id,
            "fact": fact_text
        })
    except Exception:
        logger.exception("Failed to send weekly cat fact")
        return jsonify({"error": "Failed to send cat fact"}), 500

@app.route("/api/facts/reports", methods=["GET"])
async def get_facts_reports():
    try:
        facts_raw = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="fact",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
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