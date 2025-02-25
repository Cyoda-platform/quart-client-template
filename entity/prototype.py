import asyncio
import uuid
import datetime
import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

app = Quart(__name__)
QuartSchema(app)

# In-memory storage for subscribers and email send statistics (mock persistence)
subscribers = []
email_send_stats = {
    "totalEmailsSent": 0
}

# POST /subscribe
@app.route("/subscribe", methods=["POST"])
async def subscribe():
    data = await request.get_json()
    email = data.get("email")
    name = data.get("name", "")
    if not email:
        return jsonify({"message": "Email is required"}), 400

    # Check for duplicate subscription
    for sub in subscribers:
        if sub["email"] == email:
            return jsonify({"message": "Email already subscribed"}), 400

    new_subscriber = {
        "id": str(uuid.uuid4()),  # Unique subscriber ID
        "email": email,
        "name": name,
        "subscribedAt": datetime.datetime.utcnow().isoformat()  # Timestamp for subscription
    }
    subscribers.append(new_subscriber)
    return jsonify({"message": "Subscription successful", "subscriberId": new_subscriber["id"]}), 200

# GET /subscribers
@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
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
                # Return the cat fact, or a message if not available
                return json_data.get("fact", "No fact found")
            else:
                # TODO: Enhance error handling for external API failures.
                return "Cat fact API error"

# POST /send-catfact
@app.route("/send-catfact", methods=["POST"])
async def send_catfact():
    cat_fact = await fetch_cat_fact()

    send_results = []
    for sub in subscribers:
        await send_email(sub["email"], cat_fact)
        email_send_stats["totalEmailsSent"] += 1
        send_results.append({"email": sub["email"], "status": "sent"})

    # Example of fire-and-forget processing pattern:
    # entity_job[job_id] = {"status": "processing", "requestedAt": datetime.datetime.utcnow().isoformat()}
    # await asyncio.create_task(process_entity(entity_job, data.__dict__))
    # TODO: Implement a proper asynchronous task/job queue for production.
    
    return jsonify({"message": "Cat fact sent to all subscribers", "details": send_results}), 200

# GET /report
@app.route("/report", methods=["GET"])
async def report():
    report_data = {
        "totalSubscribers": len(subscribers),
        "totalEmailsSent": email_send_stats["totalEmailsSent"],
        "additionalMetrics": {}  # TODO: Add metrics such as email open rates and click rates.
    }
    return jsonify(report_data), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)