#!/usr/bin/env python3
import asyncio
import datetime
import uuid
import aiohttp
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)  # Integrate schema validation

# Workflow function for jobs entity.
# This function is applied asynchronously before the job entity is persisted.
# It launches the background task to process scores once the job entity is saved.
async def process_jobs(entity):
    # Mark the job as processed by the workflow.
    entity["workflowProcessed"] = True
    entity["workflowProcessedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
    # Ensure the job entity has a valid identifier and a date.
    # The identifier might be returned later by the persistence layer. We try to get it if exists.
    job_id = entity.get("technical_id") or entity.get("id")
    if not job_id:
        # If no identifier, generate a temporary id which the background task can use.
        job_id = str(uuid.uuid4())
        entity["technical_id"] = job_id
    if entity.get("date"):
        # Launch the background processing task for scores.
        try:
            asyncio.create_task(process_scores(job_id, entity["date"]))
        except Exception as e:
            # Log error in launching background job.
            print(f"Error launching background processing for job {job_id}: {e}")
    else:
        print(f"Job {job_id} missing 'date' field; background processing will not be launched.")
    # Return modified entity. The returned state is what persists.
    return entity

# Workflow function for scores entity.
# This function can be used to prepare or augment scores data before persistence.
async def process_scores_workflow(entity):
    # Add workflow flag and timestamp.
    entity["workflowProcessed"] = True
    entity["workflowProcessedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
    return entity

# Workflow function for subscriptions entity.
# This function adjusts subscription entity before persisting.
async def process_subscriptions(entity):
    # Normalize email and mark processed.
    if "email" in entity and isinstance(entity["email"], str):
        entity["email"] = entity["email"].strip().lower()
    else:
        entity["email"] = ""
    entity["workflowProcessed"] = True
    entity["workflowProcessedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
    return entity

# Startup routine: initialize cyoda before serving requests.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Data models for request validation.
@dataclass
class RealTimeFetchRequest:
    date: str

@dataclass
class SubscriptionRequest:
    email: str
    team: str = ""         # Can be updated to more complex filter if needed.
    gameType: str = ""     # Can be updated to more complex filter if needed.

SPORTS_DATA_API_KEY = "f8824354d80d45368063dd2e6fb16c38"
SPORTS_DATA_URL_TEMPLATE = (
    "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=" + SPORTS_DATA_API_KEY
)

# Function to fetch scores from the external API.
async def fetch_scores_from_external(date: str):
    url = SPORTS_DATA_URL_TEMPLATE.format(date=date)
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                data = await response.json()
                return data
        except Exception as e:
            # Log and return None in case of error.
            print(f"Error fetching data from external API for date {date}: {e}")
            return None

# Background processing function for ingesting scores and updating the job status.
async def process_scores(job_technical_id: str, date: str):
    try:
        job = await entity_service.get_item(
            token=cyoda_token,
            entity_model="jobs",
            entity_version=ENTITY_VERSION,
            technical_id=job_technical_id
        )
    except Exception as e:
        print(f"Error retrieving job {job_technical_id}: {e}")
        return

    external_data = await fetch_scores_from_external(date)
    if external_data is None:
        # Update job status to 'failed' since external data could not be retrieved.
        job_update = dict(job)
        job_update["status"] = "failed"
        job_update["failedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
        try:
            await entity_service.update_item(
                token=cyoda_token,
                entity_model="jobs",
                entity_version=ENTITY_VERSION,
                entity=job_update,
                meta={}
            )
        except Exception as e:
            print(f"Error updating job {job_technical_id} to failed: {e}")
        return

    updated_games = []
    for game in external_data:
        # Determine a game identifier; fallback to generated one if missing.
        game_id = game.get("GameID") or str(uuid.uuid4())
        try:
            existing = await entity_service.get_item(
                token=cyoda_token,
                entity_model="scores",
                entity_version=ENTITY_VERSION,
                technical_id=game_id
            )
        except Exception:
            existing = None

        # Check if new data differs from existing data.
        if (not existing) or (existing.get("finalScore") != game.get("FinalScore")):
            score_data = {
                "gameId": game_id,
                "homeTeam": game.get("HomeTeam"),
                "awayTeam": game.get("AwayTeam"),
                "quarterScores": game.get("QuarterScores", []),
                "finalScore": game.get("FinalScore"),
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
            }
            if existing:
                # Update score if it exists.
                try:
                    await entity_service.update_item(
                        token=cyoda_token,
                        entity_model="scores",
                        entity_version=ENTITY_VERSION,
                        entity=score_data,
                        meta={}
                    )
                except Exception as e:
                    print(f"Error updating score for game {game_id}: {e}")
            else:
                # Add new score applying its workflow.
                try:
                    await entity_service.add_item(
                        token=cyoda_token,
                        entity_model="scores",
                        entity_version=ENTITY_VERSION,
                        entity=score_data,
                        workflow=process_scores_workflow
                    )
                except Exception as e:
                    print(f"Error adding score for game {game_id}: {e}")
            updated_games.append(score_data)

    # Update the job record with 'completed' status.
    job_update = dict(job)
    job_update["status"] = "completed"
    job_update["completedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
    try:
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="jobs",
            entity_version=ENTITY_VERSION,
            entity=job_update,
            meta={}
        )
    except Exception as e:
        print(f"Error updating job {job_technical_id} to completed: {e}")

    if updated_games:
        print(f"Job {job_technical_id} - Updated games: {updated_games}")

# POST endpoint for fetching real-time scores.
@app.route('/api/scores/fetch-real-time', methods=['POST'])
@validate_request(RealTimeFetchRequest)
async def fetch_real_time_scores(data: RealTimeFetchRequest):
    date = data.date.strip()
    if not date:
        return jsonify({"status": "error", "message": "Missing required field: date"}), 400

    requested_at = datetime.datetime.utcnow().isoformat() + "Z"
    job_data = {
        "requestedAt": requested_at,
        "status": "processing",
        "date": date
    }
    try:
        # Create the job entity with the workflow that launches background processing.
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="jobs",
            entity_version=ENTITY_VERSION,
            entity=job_data,
            workflow=process_jobs
        )
    except Exception as e:
        return jsonify({"status": "error", "message": f"Unable to create job: {e}"}), 500

    return jsonify({
        "status": "success",
        "message": "Scores fetch initiated",
        "jobId": job_id,
        "requestedAt": requested_at
    })

# GET endpoint to retrieve scores.
@app.route('/api/scores', methods=['GET'])
async def get_scores():
    date_filter = request.args.get('date', "").strip()
    game_id_filter = request.args.get('gameId', "").strip()
    condition = {}
    if game_id_filter:
        condition["gameId"] = game_id_filter
    if date_filter:
        # Assume timestamp starts with the given date string.
        condition["timestamp"] = date_filter
    try:
        if condition:
            results = await entity_service.get_items_by_condition(
                token=cyoda_token,
                entity_model="scores",
                entity_version=ENTITY_VERSION,
                condition=condition
            )
        else:
            results = await entity_service.get_items(
                token=cyoda_token,
                entity_model="scores",
                entity_version=ENTITY_VERSION
            )
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error retrieving scores: {e}"}), 500

    return jsonify({
        "status": "success",
        "results": results
    })

# POST endpoint to create a subscription.
@app.route('/api/subscriptions', methods=['POST'])
@validate_request(SubscriptionRequest)
async def create_subscription(data: SubscriptionRequest):
    email = data.email.strip()
    if not email:
        return jsonify({"status": "error", "message": "Email is required"}), 400

    filters = {
        "team": data.team.strip() if data.team else "",
        "gameType": data.gameType.strip() if data.gameType else ""
    }
    sub_data = {
        "email": email,
        "filters": filters,
        "createdAt": datetime.datetime.utcnow().isoformat() + "Z"
    }
    try:
        # Add subscription entity applying its workflow for preprocessing.
        subscription_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="subscriptions",
            entity_version=ENTITY_VERSION,
            entity=sub_data,
            workflow=process_subscriptions
        )
    except Exception as e:
        return jsonify({"status": "error", "message": f"Unable to create subscription: {e}"}), 500

    return jsonify({
        "status": "success",
        "message": "Subscription created successfully",
        "subscriptionId": subscription_id
    })

# GET endpoint to list subscriptions.
@app.route('/api/subscriptions', methods=['GET'])
async def list_subscriptions():
    try:
        results = await entity_service.get_items(
            token=cyoda_token,
            entity_model="subscriptions",
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error retrieving subscriptions: {e}"}), 500

    return jsonify({
        "status": "success",
        "subscriptions": results
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)