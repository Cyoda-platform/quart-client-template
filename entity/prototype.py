```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory "database" mock (async-safe cache)
# Use asyncio.Lock to coordinate access
class InMemoryDB:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._subscribers: List[str] = []
        self._interactions = {
            "emails_sent": 0,
            "email_opens": 0,  # TODO: Implement real tracking
            "clicks": 0,       # TODO: Implement real tracking
        }
        self._last_fact: str = ""

    async def add_subscriber(self, email: str) -> bool:
        async with self._lock:
            if email not in self._subscribers:
                self._subscribers.append(email)
                logger.info(f"Added new subscriber: {email}")
                return True
            else:
                logger.info(f"Subscriber already exists: {email}")
                return False

    async def get_subscribers(self) -> List[str]:
        async with self._lock:
            return list(self._subscribers)

    async def update_last_fact(self, fact: str):
        async with self._lock:
            self._last_fact = fact

    async def get_last_fact(self) -> str:
        async with self._lock:
            return self._last_fact

    async def increment_emails_sent(self, count: int):
        async with self._lock:
            self._interactions["emails_sent"] += count

    async def get_interactions(self) -> Dict:
        async with self._lock:
            return dict(self._interactions)


db = InMemoryDB()

CAT_FACT_API = "https://catfact.ninja/fact"

# TODO: Replace with real email sending implementation
async def send_email(to_email: str, subject: str, content: str):
    logger.info(f"Sending email to {to_email} with subject '{subject}'")
    # Simulate async email sending delay
    await asyncio.sleep(0.1)
    # TODO: Integrate with real SMTP or email provider
    return True


@app.route("/api/signup", methods=["POST"])
async def signup():
    data = await request.get_json(force=True)
    email = data.get("email")
    if not email or "@" not in email:
        return jsonify({"success": False, "message": "Invalid email"}), 400

    added = await db.add_subscriber(email)
    if added:
        return jsonify({"success": True, "message": "User subscribed successfully"})
    else:
        return jsonify({"success": True, "message": "User already subscribed"})


@app.route("/api/subscribers", methods=["GET"])
async def get_subscribers():
    subscribers = await db.get_subscribers()
    return jsonify({"subscribers": subscribers, "count": len(subscribers)})


async def fetch_cat_fact() -> str:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(CAT_FACT_API, timeout=10)
            response.raise_for_status()
            data = response.json()
            fact = data.get("fact")
            if not fact:
                raise ValueError("No 'fact' field in API response")
            logger.info(f"Fetched cat fact: {fact}")
            return fact
    except Exception as e:
        logger.exception(e)
        return "Cats are mysterious creatures!"  # fallback fact


async def process_weekly_task():
    fact = await fetch_cat_fact()
    await db.update_last_fact(fact)
    subscribers = await db.get_subscribers()
    send_tasks = []
    for email in subscribers:
        send_tasks.append(send_email(email, "Your Weekly Cat Fact 🐱", fact))
    results = await asyncio.gather(*send_tasks, return_exceptions=True)
    sent_count = sum(1 for r in results if r is True)
    await db.increment_emails_sent(sent_count)
    logger.info(f"Sent cat fact emails to {sent_count} subscribers")
    return fact, sent_count


@app.route("/api/trigger-weekly", methods=["POST"])
async def trigger_weekly():
    # Fire and forget pattern
    requested_at = datetime.utcnow().isoformat()
    entity_job = { "status": "processing", "requestedAt": requested_at }

    async def process_entity(entity_job):
        try:
            fact, sent_count = await process_weekly_task()
            entity_job["status"] = "done"
            entity_job["cat_fact"] = fact
            entity_job["emails_sent"] = sent_count
        except Exception as e:
            entity_job["status"] = "failed"
            logger.exception(e)

    asyncio.create_task(process_entity(entity_job))
    # Return immediately acknowledging processing started
    return jsonify({"success": True, "message": "Weekly cat fact sending started"}), 202


@app.route("/api/report", methods=["GET"])
async def get_report():
    subscribers = await db.get_subscribers()
    interactions = await db.get_interactions()
    return jsonify({
        "total_subscribers": len(subscribers),
        "emails_sent": interactions.get("emails_sent", 0),
        "interactions": {
            "email_opens": interactions.get("email_opens", 0),
            "clicks": interactions.get("clicks", 0),
        }
    })


if __name__ == '__main__':
    import sys
    import logging.config

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
