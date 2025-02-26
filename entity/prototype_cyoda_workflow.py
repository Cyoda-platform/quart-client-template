from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request
import asyncio
import uuid
import datetime
import aiohttp
from dataclasses import dataclass

from common.config.config import ENTITY_VERSION  # always use this constant
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# ---------------------------------------------------------------------------
# Helper async function for sending welcome email (fire-and-forget)
async def send_welcome_email(email):
    try:
        # Simulate sending a welcome email (replace with real email integration)
        await asyncio.sleep(0.1)
        print(f"Welcome email sent to {email}")
    except Exception as e:
        # Log exception here if needed
        print(f"Error sending welcome email to {email}: {e}")

# Workflow function for subscriber entity
async def process_subscriber(entity):
    try:
        # Mark entity as processed with a timestamp
        entity["workflowProcessed"] = True
        entity["processedAt"] = datetime.datetime.utcnow().isoformat()
        # Fire-and-forget: send a welcome email to the new subscriber.
        # Using create_task so that any issues inside send_welcome_email do not affect the workflow.
        asyncio.create_task(send_welcome_email(entity["email"]))
    except Exception as e:
        # In case of error, log and proceed (the error should not block the persistence)
        print(f"Error in process_subscriber workflow: {e}")
    return entity

# ---------------------------------------------------------------------------
# Helper async function for logging email_stats processing (fire-and-forget)
async def log_email_stats(entity):
    try:
        await asyncio.sleep(0.1)
        print(f"Email stats processed for record {entity.get('id','unknown')} with totalEmailsSent: {entity.get('totalEmailsSent',0)}")
    except Exception as e:
        print(f"Error in log_email_stats: {e}")

# Workflow function for email_stats entity
async def process_email_stats(entity):
    try:
        # Mark entity as processed with a timestamp
        entity["workflowProcessed"] = True
        entity["processedAt"] = datetime.datetime.utcnow().isoformat()
        # Fire-and-forget: log email stats processing.
        asyncio.create_task(log_email_stats(entity))
    except Exception as e:
        print(f"Error in process_email_stats workflow: {e}")
    return entity

# ---------------------------------------------------------------------------
# Dataclasses for request validation
@dataclass
class SubscribeData:
    email: str
    name: str = ""  # Default empty string if name is not provided

@dataclass
class EmptyData:
    # This dataclass is intentionally left empty for endpoints that expect no data.
    pass

# ---------------------------------------------------------------------------
# POST /subscribe endpoint - subscribe a new user
@app.route("/subscribe", methods=["POST"])
@validate_request(SubscribeData)
async def subscribe(data: SubscribeData):
    email = data.email
    name = data.name
    if not email:
        return jsonify({"message": "Email is required"}), 400

    # Check for duplicate subscription using external service.
    try:
        duplicate = await entity_service.get_items_by_condition(
            token=cyoda_token,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
            condition={"email": email}
        )
    except Exception as e:
        # Prevent crashing: log error and return response
        print(f"Error checking duplicate subscription for {email}: {e}")
        return jsonify({"message": "Internal server error"}), 500

    if duplicate and len(duplicate) > 0:
        return jsonify({"message": "Email already subscribed"}), 400

    new_subscriber = {
        "id": str(uuid.uuid4()),  # Unique subscriber ID
        "email": email,
        "name": name,
        "subscribedAt": datetime.datetime.utcnow().isoformat()  # Timestamp for subscription
    }
    try:
        # Add new subscriber via external service with workflow function.
        new_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
            entity=new_subscriber,
            workflow=process_subscriber
        )
    except Exception as e:
        print(f"Error adding new subscriber: {e}")
        return jsonify({"message": "Internal server error"}), 500

    return jsonify({"message": "Subscription successful", "subscriberId": new_id}), 200

# ---------------------------------------------------------------------------
# GET /subscribers endpoint - list all subscribers
@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    try:
        subscribers = await entity_service.get_items(
            token=cyoda_token,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        print(f"Error retrieving subscribers: {e}")
        return jsonify({"message": "Internal server error"}), 500

    response = {
        "count": len(subscribers),
        "subscribers": subscribers
    }
    return jsonify(response), 200

# ---------------------------------------------------------------------------
# Helper async function to send an email with cat fact (real integration can replace this)
async def send_email(email, cat_fact):
    try:
        # Simulate sending email delay.
        await asyncio.sleep(0.1)
        print(f"Email sent to {email}: {cat_fact}")
    except Exception as e:
        print(f"Error sending email to {email}: {e}")

# Helper async function to fetch cat fact from external API.
async def fetch_cat_fact():
    url = "https://catfact.ninja/fact"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    json_data = await resp.json()
                    return json_data.get("fact", "No fact found")
                else:
                    print(f"Cat fact API returned status {resp.status}")
                    return "Cat fact API error"
    except Exception as e:
        print(f"Error fetching cat fact: {e}")
        return "Cat fact fetch error"

# ---------------------------------------------------------------------------
# POST /send-catfact endpoint - send a cat fact email to all subscribers
@app.route("/send-catfact", methods=["POST"])
@validate_request(EmptyData)
async def send_catfact(data: EmptyData):
    try:
        cat_fact = await fetch_cat_fact()
    except Exception as e:
        print(f"Error in fetch_cat_fact: {e}")
        cat_fact = "Cat fact API error"

    send_results = []
    try:
        # Retrieve subscribers from the external service.
        subscribers = await entity_service.get_items(
            token=cyoda_token,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        print(f"Error retrieving subscribers for catfact: {e}")
        return jsonify({"message": "Internal server error"}), 500

    for sub in subscribers:
        try:
            await send_email(sub["email"], cat_fact)
            send_results.append({"email": sub["email"], "status": "sent"})
        except Exception as e:
            print(f"Error sending cat fact to {sub.get('email')}: {e}")
            send_results.append({"email": sub["email"], "status": "failed"})

    # Update email_stats entity: first try to update if record exists, otherwise create new with workflow function.
    try:
        stats_list = await entity_service.get_items_by_condition(
            token=cyoda_token,
            entity_model="email_stats",
            entity_version=ENTITY_VERSION,
            condition={}
        )
    except Exception as e:
        print(f"Error retrieving email_stats: {e}")
        stats_list = []

    count_sent = len(subscribers)
    try:
        if stats_list and len(stats_list) > 0:
            stats = stats_list[0]
            # Ensure totalEmailsSent exists.
            previous = stats.get("totalEmailsSent", 0)
            stats["totalEmailsSent"] = previous + count_sent
            await entity_service.update_item(
                token=cyoda_token,
                entity_model="email_stats",
                entity_version=ENTITY_VERSION,
                entity=stats,
                meta={}
            )
        else:
            new_stats = {
                "id": str(uuid.uuid4()),
                "totalEmailsSent": count_sent
            }
            await entity_service.add_item(
                token=cyoda_token,
                entity_model="email_stats",
                entity_version=ENTITY_VERSION,
                entity=new_stats,
                workflow=process_email_stats
            )
    except Exception as e:
        print(f"Error updating/adding email_stats: {e}")

    return jsonify({"message": "Cat fact processed for all subscribers", "details": send_results}), 200

# ---------------------------------------------------------------------------
# GET /report endpoint - generate a report of subscribers and email stats
@app.route("/report", methods=["GET"])
async def report():
    try:
        subscribers = await entity_service.get_items(
            token=cyoda_token,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        print(f"Error retrieving subscribers for report: {e}")
        subscribers = []

    try:
        stats_list = await entity_service.get_items_by_condition(
            token=cyoda_token,
            entity_model="email_stats",
            entity_version=ENTITY_VERSION,
            condition={}
        )
    except Exception as e:
        print(f"Error retrieving email_stats for report: {e}")
        stats_list = []

    total_emails_sent = 0
    if stats_list and len(stats_list) > 0:
        total_emails_sent = stats_list[0].get("totalEmailsSent", 0)
    report_data = {
        "totalSubscribers": len(subscribers),
        "totalEmailsSent": total_emails_sent,
        "additionalMetrics": {}  # Placeholder for additional metrics (e.g. email opens, click rates)
    }
    return jsonify(report_data), 200

# ---------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)