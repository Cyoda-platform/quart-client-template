import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Workaround for Quart-Schema validation decorator order issue:
# - For POST requests, place @validate_request after @app.route
# - For GET requests, place @validate_querystring before @app.route

@dataclass
class SubscribeRequest:
    email: str

@dataclass
class EmptyRequest:
    pass

# In-memory "persistence"
_subscribers: List[str] = []
_email_stats = {
    "emailsSent": 0,
    "emailsOpened": 0,  # TODO: Implement tracking email opens
    "clicks": 0,        # TODO: Implement tracking clicks
}
_last_fact: Dict = {}

# Simple locks for async-safe access
_subscribers_lock = asyncio.Lock()
_stats_lock = asyncio.Lock()
_fact_lock = asyncio.Lock()

CAT_FACT_API = "https://catfact.ninja/fact"

@app.route("/api/subscribe", methods=["POST"])
@validate_request(SubscribeRequest)
async def subscribe(data: SubscribeRequest):
    email = data.email
    async with _subscribers_lock:
        if email not in _subscribers:
            _subscribers.append(email)
            logger.info(f"New subscriber added: {email}")
        else:
            logger.info(f"Subscriber already exists: {email}")
    subscriber_id = str(uuid.uuid4())
    return jsonify({"message": "Subscription successful", "subscriberId": subscriber_id})

@app.route("/api/fetch-and-send", methods=["POST"])
@validate_request(EmptyRequest)
async def fetch_and_send(data: EmptyRequest):
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(CAT_FACT_API, timeout=10)
            resp.raise_for_status()
            fact_data = resp.json()
            fact = fact_data.get("fact")
            if not fact:
                logger.warning("No fact in API response")
                return jsonify({"error": "Failed to get cat fact"}), 502
        except httpx.HTTPError as e:
            logger.exception(e)
            return jsonify({"error": "External API request failed"}), 502
    async with _fact_lock:
        _last_fact["fact"] = fact
        _last_fact["fetchedAt"] = datetime.utcnow().isoformat()
    async with _subscribers_lock:
        recipients = list(_subscribers)
    if not recipients:
        logger.info("No subscribers to send emails to")
        return jsonify({"message": "No subscribers, no emails sent", "fact": fact})
    await asyncio.create_task(_send_cat_fact_emails(recipients, fact))
    return jsonify({"message": "Cat fact fetched and emails sent", "fact": fact})

async def _send_cat_fact_emails(recipients: List[str], fact: str):
    logger.info(f"Sending cat fact to {len(recipients)} subscribers")
    await asyncio.sleep(0.5)  # simulate email sending
    async with _stats_lock:
        _email_stats["emailsSent"] += len(recipients)
    logger.info("Emails sent successfully")

@app.route("/api/reporting/summary", methods=["GET"])
async def reporting_summary():
    async with _subscribers_lock:
        total_subscribers = len(_subscribers)
    async with _stats_lock:
        emails_sent = _email_stats["emailsSent"]
        emails_opened = _email_stats["emailsOpened"]
        clicks = _email_stats["clicks"]
    return jsonify({
        "totalSubscribers": total_subscribers,
        "emailsSent": emails_sent,
        "emailsOpened": emails_opened,
        "clicks": clicks,
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)