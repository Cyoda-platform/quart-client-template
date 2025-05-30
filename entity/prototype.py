```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
import uuid

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory caches to mock persistence
# Use asyncio.Lock to protect concurrent access
subscribers_lock = asyncio.Lock()
subscribers: Dict[str, Dict] = {}  # subscriberId -> {"email": str, "subscribedAt": datetime}

interactions_lock = asyncio.Lock()
interactions = {
    "emailOpens": 0,
    "clicks": 0,
}

latest_fact_lock = asyncio.Lock()
latest_fact: Optional[Dict] = None  # {"fact": str, "sentAt": datetime}

entity_jobs_lock = asyncio.Lock()
entity_jobs: Dict[str, Dict] = {}  # job_id -> job info/status


async def fetch_cat_fact() -> str:
    url = "https://catfact.ninja/fact"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            fact = data.get("fact")
            if not fact:
                raise ValueError("No 'fact' field in API response")
            return fact
        except Exception as e:
            logger.exception(f"Failed to fetch cat fact: {e}")
            raise


async def send_email(to_email: str, fact: str) -> None:
    # TODO: Replace this with real email sending integration (SMTP or API)
    logger.info(f"Mock send email to {to_email} with fact: {fact}")
    await asyncio.sleep(0.1)  # simulate network delay


async def process_entity(job_id: str) -> None:
    logger.info(f"Started processing job {job_id}")
    try:
        fact = await fetch_cat_fact()
        now = datetime.utcnow()

        async with latest_fact_lock:
            global latest_fact
            latest_fact = {"fact": fact, "sentAt": now}

        # Snapshot subscribers to avoid holding lock while sending emails
        async with subscribers_lock:
            current_subscribers = list(subscribers.values())

        # Send emails concurrently but limit concurrency to avoid overload
        semaphore = asyncio.Semaphore(10)

        async def send_to_subscriber(email: str):
            async with semaphore:
                await send_email(email, fact)

        send_tasks = [send_to_subscriber(sub["email"]) for sub in current_subscribers]
        await asyncio.gather(*send_tasks)

        # TODO: Add real interaction tracking hooks (email opens, clicks)
        logger.info(f"Sent cat fact to {len(current_subscribers)} subscribers")

        async with entity_jobs_lock:
            entity_jobs[job_id]["status"] = "completed"
            entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
    except Exception as e:
        logger.exception(f"Error processing job {job_id}: {e}")
        async with entity_jobs_lock:
            entity_jobs[job_id]["status"] = "failed"
            entity_jobs[job_id]["error"] = str(e)


@app.route("/subscribe", methods=["POST"])
async def subscribe():
    data = await request.get_json(force=True)
    email = data.get("email")
    if not email:
        return jsonify({"error": "Email is required"}), 400

    subscriber_id = str(uuid.uuid4())
    now = datetime.utcnow()

    async with subscribers_lock:
        # Simple duplicate prevention by email (optional)
        if any(sub["email"] == email for sub in subscribers.values()):
            return jsonify({"message": "Email already subscribed"}), 409
        subscribers[subscriber_id] = {"email": email, "subscribedAt": now.isoformat()}

    logger.info(f"New subscriber: {email} (id={subscriber_id})")
    return jsonify({"message": "Subscription successful", "subscriberId": subscriber_id})


@app.route("/report", methods=["GET"])
async def report():
    async with subscribers_lock:
        subs_count = len(subscribers)
    async with interactions_lock:
        email_opens = interactions.get("emailOpens", 0)
        clicks = interactions.get("clicks", 0)

    return jsonify(
        {
            "subscribersCount": subs_count,
            "emailOpens": email_opens,
            "clicks": clicks,
        }
    )


@app.route("/sendWeeklyFact", methods=["POST"])
async def send_weekly_fact():
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()
    async with entity_jobs_lock:
        entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}

    # Fire and forget processing task
    asyncio.create_task(process_entity(job_id))

    return jsonify({"message": "Weekly cat fact job started", "jobId": job_id})


@app.route("/latestFact", methods=["GET"])
async def get_latest_fact():
    async with latest_fact_lock:
        if not latest_fact:
            return jsonify({"fact": None, "message": "No fact sent yet"}), 404
        return jsonify(latest_fact)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
