```python
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory caches (async safe by design here for prototype):
subscribers: Dict[str, Dict[str, Any]] = {}
cat_facts_sent: Dict[str, Dict[str, Any]] = {}
interaction_metrics = {
    "totalEmailsSent": 0,
    "totalClicks": 0,  # TODO: Implement tracking clicks from emails (placeholder)
    "totalOpens": 0,   # TODO: Implement tracking email opens (placeholder)
}

CAT_FACT_API_URL = "https://catfact.ninja/fact"

# Mock email sending function
async def send_email(email: str, subject: str, body: str) -> None:
    # TODO: Replace with real email sending integration
    logger.info(f"Sending email to {email} with subject '{subject}' and body: {body}")
    # Simulate network latency
    await asyncio.sleep(0.1)

@app.route("/subscribe", methods=["POST"])
async def subscribe():
    data = await request.get_json()
    email = data.get("email")
    if not email:
        return jsonify({"error": "Email is required"}), 400

    # Simple uniqueness check
    if email in subscribers:
        return jsonify({"message": "Email already subscribed", "subscriberId": subscribers[email]["id"]}), 200

    subscriber_id = str(uuid.uuid4())
    subscribers[email] = {
        "id": subscriber_id,
        "email": email,
        "subscribedAt": datetime.utcnow().isoformat(),
    }
    logger.info(f"New subscriber added: {email} with id {subscriber_id}")
    return jsonify({"message": "Subscription successful", "subscriberId": subscriber_id}), 201

@app.route("/subscribers/count", methods=["GET"])
async def subscribers_count():
    count = len(subscribers)
    return jsonify({"count": count})

async def fetch_cat_fact() -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(CAT_FACT_API_URL, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            # Expected response: { "fact": "some cat fact", "length": 30 }
            return data
        except Exception as e:
            logger.exception("Failed to fetch cat fact from external API")
            raise

async def process_fact_and_send():
    # Fetch cat fact
    fact_data = await fetch_cat_fact()
    fact_text = fact_data.get("fact", "Cats are mysterious creatures.")  # fallback

    fact_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()

    # Store fact info for reporting
    cat_facts_sent[fact_id] = {
        "factText": fact_text,
        "sentAt": requested_at,
        "emailsSent": 0,
    }

    # Send emails concurrently
    send_tasks = []
    for sub in subscribers.values():
        send_tasks.append(send_email(
            sub["email"],
            subject="Your Weekly Cat Fact 🐱",
            body=fact_text,
        ))

    # Fire and forget sending emails but await here so we can count emails sent
    results = await asyncio.gather(*send_tasks, return_exceptions=True)

    # Count success
    success_count = sum(1 for r in results if not isinstance(r, Exception))
    cat_facts_sent[fact_id]["emailsSent"] = success_count
    interaction_metrics["totalEmailsSent"] += success_count

    logger.info(f"Sent cat fact '{fact_id}' to {success_count} subscribers")

    return {"factId": fact_id, "factText": fact_text, "emailsSent": success_count}

@app.route("/facts/ingest-and-send", methods=["POST"])
async def ingest_and_send():
    try:
        # Fire and forget pattern could be used but here we await to confirm result to client
        result = await process_fact_and_send()
        return jsonify(result)
    except Exception as e:
        logger.exception("Error during fact ingestion and sending")
        return jsonify({"error": "Failed to ingest and send cat fact"}), 500

@app.route("/reports/interactions", methods=["GET"])
async def reports_interactions():
    # For prototype, only basic metrics available
    return jsonify(interaction_metrics)

if __name__ == "__main__":
    import sys
    import logging

    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        level=logging.INFO,
    )

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```