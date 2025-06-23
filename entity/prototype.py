import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional

import httpx
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Workaround: validation first for GET requests, last for POST requests due to quart-schema issue

@dataclass
class SubscriptionRequest:
    email: str
    name: Optional[str] = None

@dataclass
class InteractionRequest:
    subscriberId: str
    interactionType: str
    factId: str

# In-memory "persistence"
subscribers = {}
cat_facts = {}
interactions = []

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

async def process_fetch_and_send():
    cat_fact_data = await fetch_cat_fact()
    fact_id = str(uuid.uuid4())
    fact_text = cat_fact_data.get("fact", "No fact retrieved")
    cat_facts[fact_id] = {"fact": fact_text, "createdAt": datetime.utcnow().isoformat()}
    count_sent = 0
    for sub in subscribers.values():
        try:
            await send_email(sub["email"], "Your Weekly Cat Fact 🐱", fact_text)
            count_sent += 1
        except Exception as e:
            logger.exception(f"Failed to send email to {sub['email']}: {e}")
    return count_sent, fact_id, fact_text

@app.route("/subscribe", methods=["POST"])
@validate_request(SubscriptionRequest)
async def subscribe(data: SubscriptionRequest):
    email = data.email
    name = data.name
    if not email:
        return jsonify({"message": "Email is required"}), 400
    for sub_id, sub in subscribers.items():
        if sub["email"].lower() == email.lower():
            return jsonify({"message": "Email already subscribed", "subscriberId": sub_id}), 200
    subscriber_id = str(uuid.uuid4())
    subscribers[subscriber_id] = {"email": email, "name": name}
    logger.info(f"New subscriber added: {email} (id: {subscriber_id})")
    return jsonify({"message": "Subscription successful", "subscriberId": subscriber_id}), 201

@app.route("/subscribers/count", methods=["GET"])
async def get_subscribers_count():
    return jsonify({"count": len(subscribers)})

@app.route("/fetch-and-send-fact", methods=["POST"])
async def fetch_and_send_fact():
    requested_at = datetime.utcnow().isoformat()
    try:
        count_sent, fact_id, fact_text = await process_fetch_and_send()
        return jsonify({
            "message": f"Cat fact sent to {count_sent} subscribers",
            "fact": fact_text,
            "factId": fact_id,
            "sentAt": requested_at
        })
    except Exception:
        return jsonify({"message": "Failed to fetch and send cat fact"}), 500

@app.route("/interaction", methods=["POST"])
@validate_request(InteractionRequest)
async def record_interaction(data: InteractionRequest):
    subscriber_id = data.subscriberId
    interaction_type = data.interactionType
    fact_id = data.factId
    if subscriber_id not in subscribers:
        return jsonify({"message": "Subscriber not found"}), 404
    if fact_id not in cat_facts:
        return jsonify({"message": "Fact not found"}), 404
    if interaction_type not in ("open", "click"):
        return jsonify({"message": "Invalid interactionType"}), 400
    interactions.append({
        "subscriberId": subscriber_id,
        "interactionType": interaction_type,
        "factId": fact_id,
        "timestamp": datetime.utcnow().isoformat()
    })
    logger.info(f"Recorded interaction: sub={subscriber_id}, type={interaction_type}, fact={fact_id}")
    return jsonify({"message": "Interaction recorded"})

@app.route("/interactions/report", methods=["GET"])
async def interactions_report():
    total_opens = sum(1 for i in interactions if i["interactionType"] == "open")
    total_clicks = sum(1 for i in interactions if i["interactionType"] == "click")
    return jsonify({"totalOpens": total_opens, "totalClicks": total_clicks})

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)