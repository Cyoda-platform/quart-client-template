import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class Subscription:
    email: str  # simple email field for subscription

# In-memory async-safe storage using asyncio.Lock for concurrency control
class Storage:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._subscribers: List[str] = []
        self._facts_sent: List[Dict] = []  # Stores dicts with fact text and timestamp
        self._interactions: Dict[str, int] = {"emails_sent": 0, "opens": 0, "clicks": 0}

    async def add_subscriber(self, email: str) -> bool:
        async with self._lock:
            if email not in self._subscribers:
                self._subscribers.append(email)
                logger.info(f"New subscriber added: {email}")
                return True
            else:
                logger.info(f"Email already subscribed: {email}")
                return False

    async def get_subscribers_count(self) -> int:
        async with self._lock:
            return len(self._subscribers)

    async def get_subscribers(self) -> List[str]:
        async with self._lock:
            return list(self._subscribers)

    async def add_fact_sent(self, fact: str, sent_at: datetime):
        async with self._lock:
            self._facts_sent.append({"fact": fact, "sent_at": sent_at})
            logger.info(f"Fact recorded: {fact}")

    async def increment_interaction(self, kind: str):
        async with self._lock:
            if kind in self._interactions:
                self._interactions[kind] += 1

    async def get_interactions(self) -> Dict[str, int]:
        async with self._lock:
            return dict(self._interactions)

storage = Storage()

CAT_FACT_API_URL = "https://catfact.ninja/fact"

# Dummy email sending function
async def send_email(to_email: str, subject: str, body: str):
    # TODO: Replace with real email sending implementation
    logger.info(f"Sending email to {to_email} | Subject: {subject} | Body preview: {body[:50]}...")

@app.route("/api/subscribe", methods=["POST"])
@validate_request(Subscription)  # workaround: validate_request last for POST requests due to library defect
async def subscribe(data: Subscription):
    email = data.email
    if "@" not in email:
        return jsonify({"success": False, "message": "Invalid email"}), 400
    added = await storage.add_subscriber(email)
    if not added:
        return jsonify({"success": False, "message": "Email already subscribed"}), 400
    return jsonify({"success": True, "message": "Subscription successful"})

@app.route("/api/facts/send-weekly", methods=["POST"])
async def send_weekly_fact():
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(CAT_FACT_API_URL, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            fact = data.get("fact")
            if not fact:
                logger.error("Cat fact API response missing 'fact'")
                return jsonify({"success": False, "message": "Failed to retrieve cat fact"}), 500
        except Exception as e:
            logger.exception(e)
            return jsonify({"success": False, "message": "Error fetching cat fact"}), 500

    subscribers = await storage.get_subscribers()
    send_tasks = []
    subject = "Your Weekly Cat Fact 🐱"
    for email in subscribers:
        send_tasks.append(send_email(email, subject, fact))
    await asyncio.gather(*send_tasks)
    sent_count = len(subscribers)

    now = datetime.utcnow()
    await storage.add_fact_sent(fact, now)
    await storage.increment_interaction("emails_sent")

    return jsonify({"success": True, "sentTo": sent_count, "fact": fact})

@app.route("/api/report/subscribers-count", methods=["GET"])
async def subscribers_count():
    count = await storage.get_subscribers_count()
    return jsonify({"subscribersCount": count})

@app.route("/api/report/interactions", methods=["GET"])
async def interactions():
    interactions = await storage.get_interactions()
    return jsonify({
        "totalEmailsSent": interactions.get("emails_sent", 0),
        "totalOpens": interactions.get("opens", 0),
        "totalClicks": interactions.get("clicks", 0),
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)