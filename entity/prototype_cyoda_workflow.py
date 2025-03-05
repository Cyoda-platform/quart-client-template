#!/usr/bin/env python3
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

# Initialize logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)  # Enable QuartSchema for API documentation

# External API key and URL template
SPORTS_API_KEY = "f8824354d80d45368063dd2e6fb16c38"
SPORTS_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key={key}"

# Dataclasses for request validation
@dataclass
class IngestRequest:
    date: str

@dataclass
class SubscribeRequest:
    email: str

@dataclass
class ScoresQuery:
    date: str = None  # Optional query parameter

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Workflow function for job entity.
# This function is executed asynchronously before persisting the job entity.
# It processes the raw external scores data attached to the job and creates a new scores entity.
async def process_job(entity):
    try:
        logger.info(f"Executing job workflow for entity: {entity}")
        # Simulate processing delay if needed
        await asyncio.sleep(1)
        # Extract external_data that was attached by the controller.
        # Using pop to avoid persisting it in the job entity.
        external_data = entity.pop("external_data", [])
        if not external_data:
            logger.warning("No external data found in job entity; skipping scores creation.")
        else:
            # Construct scores payload based on job entity information.
            scores_payload = {"date": entity.get("date"), "games": external_data}
            # Persist the scores entity using its workflow.
            # This is safe because it's a different entity_model ("scores"), so no recursion happens.
            await entity_service.add_item(
                token=cyoda_token,
                entity_model="scores",
                entity_version=ENTITY_VERSION,
                entity=scores_payload,
                workflow=process_scores  # Workflow function for scores entity.
            )
        # Update job entity state to reflect the outcome.
        entity["status"] = "completed"
        entity["processedAt"] = datetime.utcnow().isoformat()
        logger.info(f"Job processed for date {entity.get('date')}, records processed: {len(external_data)}.")
    except Exception as e:
        logger.exception(e)
        entity["status"] = "failed"
        entity["processedAt"] = datetime.utcnow().isoformat()
    return entity

# Workflow function for scores entity.
# Adjusts scores entity prior to persistence.
async def process_scores(entity):
    try:
        logger.info(f"Executing scores workflow for entity: {entity}")
        # Example modification: mark the record as processed.
        entity["processed"] = True
        entity["processedAt"] = datetime.utcnow().isoformat()
    except Exception as e:
        logger.exception(e)
        # In case of error, we can flag the record.
        entity["processed"] = False
    return entity

# Workflow function for subscription entity.
# Adjust subscription entity prior to persistence.
async def process_subscription(entity):
    try:
        logger.info(f"Executing subscription workflow for entity: {entity}")
        # Example: add a flag indicating that email confirmation is pending.
        entity["confirmed"] = False
        entity["subscribedAt"] = entity.get("subscribedAt", datetime.utcnow().isoformat())
    except Exception as e:
        logger.exception(e)
    return entity

@app.route("/ingest-scores", methods=["POST"])
@validate_request(IngestRequest)  # For POST, route decorator goes first, then validation.
async def ingest_scores(data: IngestRequest):
    """
    Trigger ingestion of NBA scores from the external API.
    Expects JSON: { "date": "YYYY-MM-DD" }
    """
    try:
        date = data.date
        if not date:
            return jsonify({"status": "error", "message": "Date not provided"}), 400

        # Fetch external data based on the provided date.
        url = SPORTS_API_URL.format(date=date, key=SPORTS_API_KEY)
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            external_data = response.json()

        logger.info(f"Fetched external data for date {date}: {external_data}")

        requested_at = datetime.utcnow().isoformat()
        # Create job payload including the raw external data.
        # The raw external_data is attached temporarily and will be removed in the job workflow.
        job_payload = {
            "status": "processing",
            "requestedAt": requested_at,
            "date": date,
            "external_data": external_data
        }
        # Persist the job entity with an attached workflow that processes its data.
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            entity=job_payload,
            workflow=process_job  # Workflow function for job entity.
        )

        return jsonify({
            "status": "success",
            "message": "Data ingestion complete. Processing in background.",
            "ingestedRecords": len(external_data) if external_data else 0,
            "job_id": job_id
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": "Ingestion failed"}), 500

@validate_querystring(ScoresQuery)  # For GET requests, validation decorator goes first.
@app.route("/scores", methods=["GET"])
async def get_scores():
    """
    Retrieve the processed NBA scores from the external service.
    Optional query parameter: date=YYYY-MM-DD
    """
    try:
        date = request.args.get("date")
        if date:
            condition = {"date": date}
            scores_data = await entity_service.get_items_by_condition(
                token=cyoda_token,
                entity_model="scores",
                entity_version=ENTITY_VERSION,
                condition=condition
            )
            return jsonify({"date": date, "games": scores_data})
        scores_data = await entity_service.get_items(
            token=cyoda_token,
            entity_model="scores",
            entity_version=ENTITY_VERSION,
        )
        return jsonify(scores_data)
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": "Failed to retrieve scores"}), 500

@app.route("/subscribe", methods=["POST"])
@validate_request(SubscribeRequest)  # For POST, route decorator goes first, then validation.
async def subscribe(data: SubscribeRequest):
    """
    Register a new user subscription to receive email notifications for score updates.
    Expects JSON: { "email": "user@example.com" }
    """
    try:
        email = data.email
        if not email:
            return jsonify({"status": "error", "message": "Email not provided"}), 400

        subscribed_at = datetime.utcnow().isoformat()
        subscription_payload = {"email": email, "subscribedAt": subscribed_at}
        # Persist the subscription entity with its associated workflow.
        subscription_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="subscription",
            entity_version=ENTITY_VERSION,
            entity=subscription_payload,
            workflow=process_subscription  # Workflow function for subscription entity.
        )
        logger.info(f"Created subscription {subscription_id} for email: {email}")
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
    Retrieve a list of user subscriptions from the external service.
    """
    try:
        subscriptions_data = await entity_service.get_items(
            token=cyoda_token,
            entity_model="subscription",
            entity_version=ENTITY_VERSION,
        )
        return jsonify({"subscriptions": subscriptions_data})
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": "Failed to retrieve subscriptions"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)