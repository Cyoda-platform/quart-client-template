import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Request schemas
@dataclass
class SubscribeRequest:
    email: str
    name: Optional[str] = None

@dataclass
class UnsubscribeRequest:
    email: str

# In-memory async-safe storage using asyncio.Lock for concurrency control
class AsyncStorage:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._subscribers: Dict[str, Optional[str]] = {}
        self._emails_sent = 0

    async def add_subscriber(self, email: str, name: Optional[str]) -> bool:
        async with self._lock:
            if email in self._subscribers:
                return False
            self._subscribers[email] = name
            return True

    async def remove_subscriber(self, email: str) -> bool:
        async with self._lock:
            if email in self._subscribers:
                del self._subscribers[email]
                return True
            return False

    async def get_subscribers(self) -> Dict[str, Optional[str]]:
        async with self._lock:
            return dict(self._subscribers)

    async def increment_emails_sent(self, count: int = 1):
        async with self._lock:
            self._emails_sent += count

    async def get_emails_sent(self) -> int:
        async with self._lock:
            return self._emails_sent

    async def get_total_subscribers(self) -> int:
        async with self._lock:
            return len(self._subscribers)

storage = AsyncStorage()

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
        except Exception as e:
            logger.exception("Failed to fetch cat fact")
            return None

async def send_email_stub(email: str, subject: str, body: str) -> bool:
    # TODO: Replace this stub with real email sending logic (SMTP / API)
    logger.info(f"Sending email to {email} with subject '{subject}' and body:\n{body}")
    await asyncio.sleep(0.05)
    return True

@app.route("/subscribe", methods=["POST"])
@validate_request(SubscribeRequest)  # workaround: validation must be last for POST due to quart-schema issue
async def subscribe(data: SubscribeRequest):
    email = data.email.strip().lower()
    name = data.name
    # basic email format check
    if "@" not in email or "." not in email:
        return jsonify(status="error", message="Invalid email format"), 400
    added = await storage.add_subscriber(email=email, name=name)
    if not added:
        return jsonify(status="error", message="Email already subscribed"), 400
    return jsonify(status="success", message="Subscription successful")

@app.route("/unsubscribe", methods=["POST"])
@validate_request(UnsubscribeRequest)  # workaround: validation must be last for POST due to quart-schema issue
async def unsubscribe(data: UnsubscribeRequest):
    email = data.email.strip().lower()
    removed = await storage.remove_subscriber(email=email)
    if not removed:
        return jsonify(status="error", message="Email not found"), 400
    return jsonify(status="success", message="Unsubscribed successfully")

async def process_send_weekly_fact():
    subscribers = await storage.get_subscribers()
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
    tasks = [send(email) for email in subscribers.keys()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for r in results:
        if r is True:
            success_count += 1
    await storage.increment_emails_sent(success_count)
    logger.info(f"Sent cat fact email to {success_count} subscribers")
    return success_count

@app.route("/send-weekly-fact", methods=["POST"])
async def send_weekly_fact():
    requested_at = datetime.utcnow().isoformat()
    asyncio.create_task(process_send_weekly_fact())
    return jsonify(status="success", message="Weekly cat fact sending started")

@app.route("/report/subscribers", methods=["GET"])
async def report_subscribers():
    total = await storage.get_total_subscribers()
    return jsonify(total_subscribers=total)

@app.route("/report/emails-sent", methods=["GET"])
async def report_emails_sent():
    total = await storage.get_emails_sent()
    return jsonify(total_emails_sent=total)

if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
        level=logging.INFO,
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)