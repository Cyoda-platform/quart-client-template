import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

# Initialize logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)  # Enable QuartSchema for API documentation, without request validation

# In-memory caches (mock persistence)
scores_cache = {}  # { date_str: [list of game dicts] }
subscriptions = {}  # { subscription_id: { "email": "user@example.com", "subscribedAt": timestamp } }
entity_jobs = {}  # For demo purposes: { job_id: { "status": ..., "requestedAt": ... } }

# External API key and URL template
SPORTS_API_KEY = "f8824354d80d45368063dd2e6fb16c38"
SPORTS_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key={key}"


async def process_scores(job_id: str, date: str, data: list):
    """
    Process the ingested scores data and update the local cache.
    This function simulates processing delays and any additional data transformation.
    """
    try:
        logger.info(f"Processing job {job_id} for date {date}.")
        # TODO: Add any additional calculations or processing logic here if needed
        # Simulate processing delay
        await asyncio.sleep(1)
        scores_cache[date] = data
        entity_jobs[job_id]["status"] = "completed"
        logger.info(f"Job {job_id} completed. Processed {len(data)} records for date {date}.")
    except Exception as e:
        logger.exception(e)
        entity_jobs[job_id]["status"] = "failed"


@app.route("/ingest-scores", methods=["POST"])
async def ingest_scores():
    """
    Trigger ingestion of NBA scores from the external API.
    Expects JSON: { "date": "YYYY-MM-DD" }
    """
    try:
        req_data = await request.get_json()
        date = req_data.get("date")
        if not date:
            return jsonify({"status": "error", "message": "Date not provided"}), 400

        # Construct external API URL
        url = SPORTS_API_URL.format(date=date, key=SPORTS_API_KEY)
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            external_data = response.json()

        # Log ingestion start
        logger.info(f"Ingested data for date {date}: {external_data}")

        # Create a job entry for processing (fire and forget)
        job_id = str(uuid.uuid4())
        requested_at = datetime.utcnow().isoformat()
        entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}
        # Fire and forget task to process the data
        asyncio.create_task(process_scores(job_id, date, external_data))

        return jsonify({
            "status": "success",
            "message": "Data ingestion complete. Processing in background.",
            "ingestedRecords": len(external_data),
            "job_id": job_id
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": "Ingestion failed"}), 500


@app.route("/scores", methods=["GET"])
async def get_scores():
    """
    Retrieve the processed NBA scores from the internal data store.
    Optional query parameter: date=YYYY-MM-DD
    """
    date = request.args.get("date")
    if date:
        data = scores_cache.get(date, [])
        return jsonify({"date": date, "games": data})
    # If no date filter is provided, return all scores by date
    return jsonify(scores_cache)


@app.route("/subscribe", methods=["POST"])
async def subscribe():
    """
    Register a new user subscription to receive email notifications for score updates.
    Expects JSON: { "email": "user@example.com" }
    """
    try:
        req_data = await request.get_json()
        email = req_data.get("email")
        if not email:
            return jsonify({"status": "error", "message": "Email not provided"}), 400

        subscription_id = str(uuid.uuid4())
        subscriptions[subscription_id] = {
            "email": email,
            "subscribedAt": datetime.utcnow().isoformat()
        }
        # TODO: Trigger actual email service integration for confirmation, if needed.
        logger.info(f"New subscription created: {subscription_id} for email: {email}")
        return jsonify({
            "status": "success",
            "message": "Subscription created successfully.",
            "subscriptionId": subscription_id
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": "Subscription failed"}), 500


@app.route("/subscriptions", methods=["GET"])
async def get_subscriptions():
    """
    Retrieve a list of user subscriptions.
    """
    return jsonify({"subscriptions": list(subscriptions.values())})


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)