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

# Dataclasses for request validation
@dataclass
class SubscribeData:
    email: str
    name: str = ""  # Default empty string if name is not provided

@dataclass
class EmptyData:
    # This dataclass is intentionally left empty for endpoints that expect no data.
    pass

# POST /subscribe
@app.route("/subscribe", methods=["POST"])
@validate_request(SubscribeData)  # Workaround: For POST endpoints, validation decorator comes after route decorator.
async def subscribe(data: SubscribeData):
    email = data.email
    name = data.name
    if not email:
        return jsonify({"message": "Email is required"}), 400

    # Check for duplicate subscription using external service
    duplicate = await entity_service.get_items_by_condition(
        token=cyoda_token,
        entity_model="subscriber",
        entity_version=ENTITY_VERSION,
        condition={"email": email}
    )
    if duplicate and len(duplicate) > 0:
        return jsonify({"message": "Email already subscribed"}), 400

    new_subscriber = {
        "id": str(uuid.uuid4()),  # Unique subscriber ID
        "email": email,
        "name": name,
        "subscribedAt": datetime.datetime.utcnow().isoformat()  # Timestamp for subscription
    }
    # Add new subscriber via external service
    new_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="subscriber",
        entity_version=ENTITY_VERSION,
        entity=new_subscriber
    )
    return jsonify({"message": "Subscription successful", "subscriberId": new_id}), 200

# GET /subscribers
@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    subscribers = await entity_service.get_items(
        token=cyoda_token,
        entity_model="subscriber",
        entity_version=ENTITY_VERSION,
    )
    response = {
        "count": len(subscribers),
        "subscribers": subscribers
    }
    return jsonify(response), 200

# Async function to simulate email sending
async def send_email(email, cat_fact):
    # TODO: Replace with integration to a real email service provider.
    await asyncio.sleep(0.1)  # Simulate email sending delay
    print(f"Email sent to {email}: {cat_fact}")

# Function to retrieve a random cat fact from external API
async def fetch_cat_fact():
    url = "https://catfact.ninja/fact"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                json_data = await resp.json()
                return json_data.get("fact", "No fact found")
            else:
                # TODO: Enhance error handling for external API failures.
                return "Cat fact API error"

# POST /send-catfact
@app.route("/send-catfact", methods=["POST"])
@validate_request(EmptyData)  # Workaround: For POST endpoints, validation decorator comes after route decorator even if no data is expected.
async def send_catfact(data: EmptyData):
    cat_fact = await fetch_cat_fact()
    send_results = []

    # Retrieve subscribers from the external service
    subscribers = await entity_service.get_items(
        token=cyoda_token,
        entity_model="subscriber",
        entity_version=ENTITY_VERSION,
    )
    for sub in subscribers:
        await send_email(sub["email"], cat_fact)
        send_results.append({"email": sub["email"], "status": "sent"})
    
    # Update email send statistics via external service using "email_stats" entity model
    # Try to retrieve existing email_stats record; assume there is only one record.
    stats_list = await entity_service.get_items_by_condition(
        token=cyoda_token,
        entity_model="email_stats",
        entity_version=ENTITY_VERSION,
        condition={}
    )
    count_sent = len(subscribers)
    if stats_list and len(stats_list) > 0:
        stats = stats_list[0]
        # Ensure totalEmailsSent exists
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
        # Create a new email_stats record
        new_stats = {
            "id": str(uuid.uuid4()),
            "totalEmailsSent": count_sent
        }
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="email_stats",
            entity_version=ENTITY_VERSION,
            entity=new_stats
        )
    
    return jsonify({"message": "Cat fact sent to all subscribers", "details": send_results}), 200

# GET /report
@app.route("/report", methods=["GET"])
async def report():
    # Get subscribers count from external service
    subscribers = await entity_service.get_items(
        token=cyoda_token,
        entity_model="subscriber",
        entity_version=ENTITY_VERSION,
    )
    # Get email send statistics from external service
    stats_list = await entity_service.get_items_by_condition(
        token=cyoda_token,
        entity_model="email_stats",
        entity_version=ENTITY_VERSION,
        condition={}
    )
    total_emails_sent = 0
    if stats_list and len(stats_list) > 0:
        total_emails_sent = stats_list[0].get("totalEmailsSent", 0)
    report_data = {
        "totalSubscribers": len(subscribers),
        "totalEmailsSent": total_emails_sent,
        "additionalMetrics": {}  # TODO: Add metrics such as email open rates and click rates.
    }
    return jsonify(report_data), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)