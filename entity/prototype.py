```python
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory async-safe caches
# We will protect these caches with asyncio.Lock for concurrency safety.
class Cache:
    def __init__(self):
        self._subscribers: List[str] = []
        self._latest_fact: Dict = {}
        self._report = {
            "subscriberCount": 0,
            "factsSent": 0,
            "lastSentAt": None,
        }
        self._lock = asyncio.Lock()

    async def add_subscriber(self, email: str) -> bool:
        async with self._lock:
            if email in self._subscribers:
                return False
            self._subscribers.append(email)
            self._report["subscriberCount"] = len(self._subscribers)
            return True

    async def get_subscribers(self) -> List[str]:
        async with self._lock:
            return list(self._subscribers)

    async def update_latest_fact(self, fact: str):
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            self._latest_fact = {"catFact": fact, "sentAt": now}
            self._report["factsSent"] += 1
            self._report["lastSentAt"] = now

    async def get_latest_fact(self) -> Dict:
        async with self._lock:
            return dict(self._latest_fact)

    async def get_report(self) -> Dict:
        async with self._lock:
            return dict(self._report)


cache = Cache()

# Email sending is mocked here - TODO: Replace with real email sending service integration
async def send_email(to_email: str, cat_fact: str):
    # Simulate email sending latency
    await asyncio.sleep(0.1)
    logger.info(f"Sent cat fact email to {to_email}")
    # TODO: Integrate with real email service provider (SMTP, SendGrid, etc.)

# Fetch cat fact from external real API (https://catfact.ninja/fact)
async def fetch_cat_fact() -> str:
    url = "https://catfact.ninja/fact"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            fact = data.get("fact")
            if not fact:
                raise ValueError("No 'fact' field in response from Cat Fact API")
            return fact
        except (httpx.HTTPError, ValueError) as e:
            logger.exception(f"Failed to fetch cat fact: {e}")
            raise

@app.route("/api/subscribers", methods=["POST"])
async def subscribe():
    data = await request.get_json(force=True)
    email = data.get("email", "").strip().lower()
    if not email or "@" not in email:
        return jsonify({"error": "Invalid or missing email"}), 400

    added = await cache.add_subscriber(email)
    if not added:
        return jsonify({"error": "Email already subscribed"}), 400

    logger.info(f"New subscriber added: {email}")
    return "", 201

@app.route("/api/subscribers", methods=["GET"])
async def list_subscribers():
    subscribers = await cache.get_subscribers()
    return jsonify({"subscribers": [{"email": e} for e in subscribers], "count": len(subscribers)}), 200

@app.route("/api/catfact/send", methods=["POST"])
async def send_cat_fact():
    subscribers = await cache.get_subscribers()
    if not subscribers:
        return jsonify({"error": "No subscribers to send emails to"}), 400

    try:
        cat_fact = await fetch_cat_fact()
    except Exception:
        return jsonify({"error": "Failed to fetch cat fact"}), 500

    # Fire and forget sending emails concurrently, but wait for all to finish here to report count
    async def send_all_emails():
        await asyncio.gather(*(send_email(email, cat_fact) for email in subscribers))

    await send_all_emails()

    await cache.update_latest_fact(cat_fact)
    logger.info(f"Cat fact sent to {len(subscribers)} subscribers")

    return jsonify({"catFact": cat_fact, "emailsSent": len(subscribers)}), 200

@app.route("/api/catfact/latest", methods=["GET"])
async def get_latest_cat_fact():
    latest = await cache.get_latest_fact()
    if not latest:
        return jsonify({"error": "No cat fact sent yet"}), 404
    return jsonify(latest), 200

@app.route("/api/report", methods=["GET"])
async def get_report():
    report = await cache.get_report()
    return jsonify(report), 200


if __name__ == '__main__':
    import sys
    import logging

    logging.basicConfig(
        format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        level=logging.INFO,
        stream=sys.stdout,
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
