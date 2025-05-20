```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, List
from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory "persistence"
_subscribers: List[str] = []
_email_stats = {
    "emailsSent": 0,
    "emailsOpened": 0,  # TODO: Implement tracking email opens (placeholder)
    "clicks": 0,        # TODO: Implement tracking clicks (placeholder)
}
_last_fact: Dict = {}

CAT_FACT_API = "https://catfact.ninja/fact"

# Simple lock for async-safe access to shared data
_subscribers_lock = asyncio.Lock()
_stats_lock = asyncio.Lock()
_fact_lock = asyncio.Lock()


@app.route("/api/subscribe", methods=["POST"])
async def subscribe():
    data = await request.get_json()
    email = data.get("email")
    if not email or not isinstance(email, str):
        return jsonify({"error": "Invalid or missing email"}), 400

    async with _subscribers_lock:
        if email not in _subscribers:
            _subscribers.append(email)
            logger.info(f"New subscriber added: {email}")
        else:
            logger.info(f"Subscriber already exists: {email}")

    # Generate a simple UUID for subscriberId placeholder
    import uuid
    subscriber_id = str(uuid.uuid4())

    return jsonify({"message": "Subscription successful", "subscriberId": subscriber_id})


@app.route("/api/fetch-and-send", methods=["POST"])
async def fetch_and_send():
    # Fetch cat fact from external API
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(CAT_FACT_API, timeout=10)
            resp.raise_for_status()
            fact_data = resp.json()
            fact = fact_data.get("fact")
            if not fact:
                logger.warning("Cat fact API returned no fact")
                return jsonify({"error": "Failed to get cat fact"}), 502
        except httpx.HTTPError as e:
            logger.exception(e)
            return jsonify({"error": "External API request failed"}), 502

    # Save last fact
    async with _fact_lock:
        _last_fact["fact"] = fact
        _last_fact["fetchedAt"] = datetime.utcnow().isoformat()

    # Simulate sending emails to all subscribers
    async with _subscribers_lock:
        recipients = list(_subscribers)

    if not recipients:
        logger.info("No subscribers to send emails to")
        return jsonify({"message": "No subscribers, no emails sent", "fact": fact})

    # Fire and forget sending emails
    await asyncio.create_task(_send_cat_fact_emails(recipients, fact))

    return jsonify({"message": "Cat fact fetched and emails sent", "fact": fact})


async def _send_cat_fact_emails(recipients: List[str], fact: str):
    # TODO: Replace with real email sending logic.
    # Here we just simulate a small delay and log.
    logger.info(f"Sending cat fact to {len(recipients)} subscribers")
    await asyncio.sleep(0.5)  # simulate email sending delay

    async with _stats_lock:
        _email_stats["emailsSent"] += len(recipients)

    logger.info("Emails sent successfully")


@app.route("/api/reporting/summary", methods=["GET"])
async def reporting_summary():
    async with _subscribers_lock:
        total_subscribers = len(_subscribers)
    async with _stats_lock:
        emails_sent = _email_stats["emailsSent"]
        emails_opened = _email_stats["emailsOpened"]  # still zero, placeholder
        clicks = _email_stats["clicks"]                # still zero, placeholder

    return jsonify({
        "totalSubscribers": total_subscribers,
        "emailsSent": emails_sent,
        "emailsOpened": emails_opened,
        "clicks": clicks,
    })


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
