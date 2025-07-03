```python
import asyncio
import logging
from datetime import datetime, timezone
import uuid

from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory "database" caches for prototype
subscribers_cache = {}
facts_cache = {}
# facts_cache structure:
# fact_id : {
#   "fact": str,
#   "sentDate": datetime,
#   "emailsSent": int,
#   "emailsOpened": int,      # TODO: mock or simulate opens
#   "linksClicked": int       # TODO: mock or simulate clicks
# }

async def fetch_cat_fact() -> dict:
    url = "https://catfact.ninja/fact"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return data  # expected: {"fact": "...", "length": int}
        except Exception as e:
            logger.exception("Failed to fetch cat fact")
            raise e

async def send_email_stub(email: str, fact: str):
    # TODO: Replace this stub with real email sending service integration
    # For prototype, just log the event
    logger.info(f"Sending email to {email} with cat fact: {fact}")
    await asyncio.sleep(0.05)  # simulate some delay

async def process_weekly_fact_send():
    try:
        cat_fact_data = await fetch_cat_fact()
        fact_text = cat_fact_data.get("fact", "Cats are mysterious creatures!")
        fact_id = str(uuid.uuid4())
        sent_date = datetime.now(timezone.utc).isoformat()

        # Store the fact for reporting
        facts_cache[fact_id] = {
            "fact": fact_text,
            "sentDate": sent_date,
            "emailsSent": 0,
            "emailsOpened": 0,   # TODO: simulate or track real opens later
            "linksClicked": 0    # TODO: simulate or track real clicks later
        }

        # Send emails concurrently, fire-and-forget pattern
        send_tasks = []
        for subscriber in subscribers_cache.values():
            send_tasks.append(send_email_stub(subscriber["email"], fact_text))
        await asyncio.gather(*send_tasks)

        facts_cache[fact_id]["emailsSent"] = len(subscribers_cache)

        return fact_id, fact_text
    except Exception as e:
        logger.exception("Error processing weekly fact send")
        raise e

@app.route("/api/signup", methods=["POST"])
async def signup():
    data = await request.get_json()
    email = data.get("email")
    if not email:
        return jsonify({"error": "Email is required"}), 400
    name = data.get("name")

    # Avoid duplicates by email
    if email in (s["email"] for s in subscribers_cache.values()):
        return jsonify({"message": "Email already subscribed"}), 409

    subscriber_id = str(uuid.uuid4())
    subscribers_cache[subscriber_id] = {"email": email, "name": name}
    logger.info(f"New subscriber added: {email}")
    return jsonify({"message": "Subscription successful", "subscriberId": subscriber_id})

@app.route("/api/subscribers", methods=["GET"])
async def get_subscribers():
    count_only = request.args.get("countOnly", "false").lower() == "true"
    if count_only:
        return jsonify({"totalSubscribers": len(subscribers_cache)})
    else:
        subs_list = [
            {"id": sid, "email": sub["email"], "name": sub["name"]}
            for sid, sub in subscribers_cache.items()
        ]
        return jsonify({"totalSubscribers": len(subscribers_cache), "subscribers": subs_list})

@app.route("/api/facts/sendWeekly", methods=["POST"])
async def send_weekly_fact():
    # Fire and forget processing task but wait for completion here to confirm send
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
    import logging

    # Setup basic console logging
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
