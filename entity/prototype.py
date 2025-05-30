import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import uuid

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data models for request validation
@dataclass
class SubscribeRequest:
    email: str

# In-memory caches to mock persistence
subscribers_lock = asyncio.Lock()
subscribers: Dict[str, Dict] = {}

interactions_lock = asyncio.Lock()
interactions = {"emailOpens": 0, "clicks": 0}

latest_fact_lock = asyncio.Lock()
latest_fact: Optional[Dict] = None

entity_jobs_lock = asyncio.Lock()
entity_jobs: Dict[str, Dict] = {}

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
    await asyncio.sleep(0.1)

async def process_entity(job_id: str) -> None:
    logger.info(f"Started processing job {job_id}")
    try:
        fact = await fetch_cat_fact()
        now = datetime.utcnow()

        async with latest_fact_lock:
            global latest_fact
            latest_fact = {"fact": fact, "sentAt": now}

        async with subscribers_lock:
            current_subscribers = list(subscribers.values())

        semaphore = asyncio.Semaphore(10)
        async def send_to_subscriber(email: str):
            async with semaphore:
                await send_email(email, fact)
        await asyncio.gather(*[send_to_subscriber(sub["email"]) for sub in current_subscribers])

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
@validate_request(SubscribeRequest)  # workaround: POST validators must be last due to library issue
async def subscribe(data: SubscribeRequest):
    email = data.email
    subscriber_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    async with subscribers_lock:
        if any(sub["email"] == email for sub in subscribers.values()):
            return jsonify({"message": "Email already subscribed"}), 409
        subscribers[subscriber_id] = {"email": email, "subscribedAt": now}

    logger.info(f"New subscriber: {email} (id={subscriber_id})")
    return jsonify({"message": "Subscription successful", "subscriberId": subscriber_id})

@app.route("/report", methods=["GET"])
async def report():
    async with subscribers_lock:
        subs_count = len(subscribers)
    async with interactions_lock:
        email_opens = interactions.get("emailOpens", 0)
        clicks = interactions.get("clicks", 0)
    return jsonify({"subscribersCount": subs_count, "emailOpens": email_opens, "clicks": clicks})

@app.route("/sendWeeklyFact", methods=["POST"])
async def send_weekly_fact():
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()
    async with entity_jobs_lock:
        entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}
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