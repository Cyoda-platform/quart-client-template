from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional
from uuid import uuid4

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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

    if any(s["email"] == email for s in subscribers.values()):
        return jsonify({"error": "Email already subscribed"}), 400

    subscriber_id = str(uuid4())
    subscribers[subscriber_id] = {
        "id": subscriber_id,
        "email": email,
        "name": name,
        "subscribedAt": datetime.utcnow().isoformat(),
    }
    logger.info(f"New subscriber: {email} (id={subscriber_id})")
    return jsonify({"message": "Subscription successful", "subscriberId": subscriber_id})

@app.route("/subscribers/count", methods=["GET"])
async def get_subscriber_count():
    count = len(subscribers)
    return jsonify({"subscriberCount": count})

@app.route("/fetch-and-send-catfact", methods=["POST"])
async def fetch_and_send_catfact():
    fact = await fetch_cat_fact()
    if not fact:
        return jsonify({"error": "Failed to fetch cat fact"}), 500

    emails_sent = 0
    async def send_to_subscriber(sub):
        nonlocal emails_sent
        subject = "Your Weekly Cat Fact! 🐱"
        body = f"Hello{f' {sub.get('name')}' if sub.get('name') else ''},\n\nHere's your cat fact this week:\n\n{fact}\n\nEnjoy!"
        try:
            sent = await send_email(sub["email"], subject, body)
            if sent:
                emails_sent += 1
        except Exception as e:
            logger.exception(f"Failed to send email to {sub['email']}: {e}")

    tasks = [send_to_subscriber(sub) for sub in subscribers.values()]
    await asyncio.gather(*tasks)

    interaction_metrics["emailsSent"] += emails_sent
    logger.info(f"Sent cat fact to {emails_sent} subscribers")
    return jsonify({"message": "Cat fact fetched and emails sent", "fact": fact, "emailsSent": emails_sent})

@app.route("/report/interactions", methods=["GET"])
async def get_interactions_report():
    return jsonify(interaction_metrics)

# In-memory "persistence" containers for prototype
subscribers: Dict[str, Dict] = {}
interaction_metrics: Dict[str, int] = {
    "emailsSent": 0,
    "emailsOpened": 0,  # TODO: Implement email open tracking (mocked here)
    "clicks": 0,        # TODO: Implement link click tracking (mocked here)
}

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