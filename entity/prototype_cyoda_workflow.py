#!/usr/bin/env python3
import asyncio
import logging
import uuid
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

# Workflow function for job entity
async def process_job(entity):
    # You can modify the job entity prior to persistence if needed
    logger.info(f"Workflow processing for job entity: {entity}")
    # For example, add a workflowProcessed timestamp
    entity["workflowProcessed"] = datetime.utcnow().isoformat()
    return entity

# Workflow function for scores entity
async def process_scores(entity):
    # Process the scores entity before persistence
    logger.info(f"Workflow processing for scores entity: {entity}")
    # For example, add a processed flag
    entity["processed"] = True
    return entity

# Workflow function for subscription entity
async def process_subscription(entity):
    # Process the subscription entity before persistence
    logger.info(f"Workflow processing for subscription entity: {entity}")
    # For example, add a confirmed flag defaulting to False
    entity["confirmed"] = False
    return entity

# Background task to process job data (renamed from process_scores to avoid conflict)
async def process_job_data(job_id: str, date: str, data: list):
    """
    Process the ingested scores data and update the external service.
    This function simulates processing delays and any additional data transformation.
    """
    try:
        logger.info(f"Processing job {job_id} for date {date}.")
        # Simulate processing delay
        await asyncio.sleep(1)
        # Add scores record to external service with workflow function process_scores
        scores_payload = {"date": date, "games": data}
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="scores",
            entity_version=ENTITY_VERSION,
            entity=scores_payload,
            workflow=process_scores  # Workflow function for scores entity
        )
        # Update job status to completed in external service
        update_payload = {"status": "completed"}
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            entity=update_payload,
            technical_id=job_id,
            meta={}
        )
        logger.info(f"Job {job_id} completed. Processed {len(data)} records for date {date}.")
    except Exception as e:
        logger.exception(e)
        # Update job status to failed in external service
        update_payload = {"status": "failed"}
        try:
            await entity_service.update_item(
                token=cyoda_token,
                entity_model="job",
                entity_version=ENTITY_VERSION,
                entity=update_payload,
                technical_id=job_id,
                meta={}
            )
        except Exception as ex:
            logger.exception(ex)

@app.route("/ingest-scores", methods=["POST"])
@validate_request(IngestRequest)  # Workaround: For POST, route decorator goes first, then validation.
async def ingest_scores(data: IngestRequest):
    """
    Trigger ingestion of NBA scores from the external API.
    Expects JSON: { "date": "YYYY-MM-DD" }
    """
    try:
        date = data.date
        if not date:
            return jsonify({"status": "error", "message": "Date not provided"}), 400

        # Construct external API URL
        url = SPORTS_API_URL.format(date=date, key=SPORTS_API_KEY)
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            external_data = response.json()

        logger.info(f"Ingested data for date {date}: {external_data}")

        requested_at = datetime.utcnow().isoformat()
        # Create a job entry in the external service for processing, using workflow for job entities
        job_payload = {"status": "processing", "requestedAt": requested_at, "date": date}
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            entity=job_payload,
            workflow=process_job  # Workflow function for job entity
        )

        # Fire and forget task to process the data
        asyncio.create_task(process_job_data(job_id, date, external_data))

        return jsonify({
            "status": "success",
            "message": "Data ingestion complete. Processing in background.",
            "ingestedRecords": len(external_data),
            "job_id": job_id
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": "Ingestion failed"}), 500

@validate_querystring(ScoresQuery)  # Workaround: For GET requests, validation decorator goes first.
@app.route("/scores", methods=["GET"])
async def get_scores():
    """
    Retrieve the processed NBA scores from the external service.
    Optional query parameter: date=YYYY-MM-DD
    """
    try:
        date = request.args.get("date")
        if date:
            # Retrieve scores by condition from external service
            condition = {"date": date}
            scores_data = await entity_service.get_items_by_condition(
                token=cyoda_token,
                entity_model="scores",
                entity_version=ENTITY_VERSION,
                condition=condition
            )
            return jsonify({"date": date, "games": scores_data})
        # Retrieve all scores from external service
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
@validate_request(SubscribeRequest)  # Workaround: For POST, route decorator goes first, then validation.
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
        subscription_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="subscription",
            entity_version=ENTITY_VERSION,
            entity=subscription_payload,
            workflow=process_subscription  # Workflow function for subscription entity
        )
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