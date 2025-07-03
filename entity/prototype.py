from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime, timezone
import uuid

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class SignupRequest:
    email: str
    name: str = None

@dataclass
class SubscriberQuery:
    countOnly: bool = False

async def fetch_cat_fact() -> dict:
    url = "https://catfact.ninja/fact"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.exception("Failed to fetch cat fact")
            raise e

async def send_email_stub(email: str, fact: str):
    logger.info(f"Sending email to {email} with cat fact: {fact}")
    await asyncio.sleep(0.05)

async def process_weekly_fact_send():
    try:
        cat_fact_data = await fetch_cat_fact()
        fact_text = cat_fact_data.get("fact", "Cats are mysterious creatures!")
        fact_id = str(uuid.uuid4())
        sent_date = datetime.now(timezone.utc).isoformat()

        facts_cache[fact_id] = {
            "fact": fact_text,
            "sentDate": sent_date,
            "emailsSent": 0,
            "emailsOpened": 0,
            "linksClicked": 0
        }

        send_tasks = []
        for subscriber in subscribers_cache.values():
            send_tasks.append(send_email_stub(subscriber["email"], fact_text))
        await asyncio.gather(*send_tasks)

        facts_cache[fact_id]["emailsSent"] = len(subscribers_cache)
        return fact_id, fact_text
    except Exception as e:
        logger.exception("Error processing weekly fact send")
        raise e

subscribers_cache = {}
facts_cache = {}

@app.route("/api/signup", methods=["POST"])
@validate_request(SignupRequest)  # validation last for POST (workaround for library issue)
async def signup(data: SignupRequest):
    email = data.email
    if not email:
        return jsonify({"error": "Email is required"}), 400
    if email in (s["email"] for s in subscribers_cache.values()):
        return jsonify({"message": "Email already subscribed"}), 409
    subscriber_id = str(uuid.uuid4())
    subscribers_cache[subscriber_id] = {"email": email, "name": data.name}
    logger.info(f"New subscriber added: {email}")
    return jsonify({"message": "Subscription successful", "subscriberId": subscriber_id})

@validate_querystring(SubscriberQuery)  # validation first for GET (workaround for library issue)
@app.route("/api/subscribers", methods=["GET"])
async def get_subscribers():
    args = SubscriberQuery(**request.args)
    if args.countOnly:
        return jsonify({"totalSubscribers": len(subscribers_cache)})
    subs_list = [
        {"id": sid, "email": sub["email"], "name": sub["name"]}
        for sid, sub in subscribers_cache.items()
    ]
    return jsonify({"totalSubscribers": len(subscribers_cache), "subscribers": subs_list})

@app.route("/api/facts/sendWeekly", methods=["POST"])
async def send_weekly_fact():
    try:
        fact_id, fact_text = await process_weekly_fact_send()
        return jsonify({
            "message": "Cat fact sent to subscribers",
            "factId": fact_id,
            "fact": fact_text
        })
    except Exception:
        return jsonify({"error": "Failed to send cat fact"}), 500

@app.route("/api/facts/reports", methods=["GET"])
async def get_facts_reports():
    facts_list = []
    for fid, info in facts_cache.items():
        facts_list.append({
            "factId": fid,
            "fact": info["fact"],
            "sentDate": info["sentDate"],
            "emailsSent": info["emailsSent"],
            "emailsOpened": info["emailsOpened"],
            "linksClicked": info["linksClicked"]
        })
    return jsonify({"facts": facts_list})

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)