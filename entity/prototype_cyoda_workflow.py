#!/usr/bin/env python3
import asyncio
import datetime
import uuid
import aiohttp
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request  # validate_querystring imported if needed
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)  # Schema integration for request/response validation

# Workflow function for jobs entity
# It will launch the background processing function for scores asynchronously.
async def process_jobs(entity):
    # Mark the job as processed by workflow.
    entity["workflowProcessed"] = True
    entity["workflowProcessedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
    # Launch the background task with the job's id and date.
    # We assume that the job entity already contains a 'date' field.
    job_id = entity.get("technical_id") or entity.get("id")
    if job_id and entity.get("date"):
        asyncio.create_task(process_scores(job_id, entity["date"]))
    return entity

# Workflow function for scores entity
async def process_scores_workflow(entity):
    # Add a workflow flag and a workflow timestamp to the score data.
    entity["workflowProcessed"] = True
    entity["workflowProcessedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
    return entity

# Workflow function for subscriptions entity
async def process_subscriptions(entity):
    # Lower-case the email and mark the subscription as processed.
    entity["email"] = entity.get("email", "").lower()
    entity["workflowProcessed"] = True
    entity["workflowProcessedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
    return entity

# Startup routine to initialize cyoda
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Data models for request validation
@dataclass
class RealTimeFetchRequest:
    date: str

@dataclass
class SubscriptionRequest:
    email: str
    team: str = ""         # TODO: Update type if more complex filter is needed
    gameType: str = ""     # TODO: Update type if more complex filter is needed

SPORTS_DATA_API_KEY = "f8824354d80d45368063dd2e6fb16c38"
SPORTS_DATA_URL_TEMPLATE = (
    "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=" + SPORTS_DATA_API_KEY
)

# Function to call external API and fetch score data
async def fetch_scores_from_external(date: str):
    url = SPORTS_DATA_URL_TEMPLATE.format(date=date)
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                data = await response.json()
                return data
        except Exception as e:
            # TODO: Add proper error handling and logging
            print(f"Error fetching data from external API: {e}")
            return None

# Background processing function for score ingestion and updating job status
async def process_scores(job_technical_id: str, date: str):
    # Retrieve job record from external service
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
        # Update job status to failed
        job_update = dict(job)
        job_update["status"] = "failed"
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
                try:
                    # Persist the new score entity applying its workflow before saving.
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

    # Update job record with completion status
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
        print(f"Job {job_technical_id} - Score updates detected and events published: {updated_games}")

# POST endpoint: fetch real-time scores
# NOTE: Workaround for quart-schema issue: for POST requests, route decorator goes first, then validation.
@app.route('/api/scores/fetch-real-time', methods=['POST'])
@validate_request(RealTimeFetchRequest)  # This decorator is added second per workaround
async def fetch_real_time_scores(data: RealTimeFetchRequest):
    date = data.date
    if not date:
        return jsonify({"status": "error", "message": "Missing required field: date"}), 400

    requested_at = datetime.datetime.utcnow().isoformat() + "Z"
    job_data = {
        "requestedAt": requested_at,
        "status": "processing",
        "date": date
    }
    try:
        # The workflow function process_jobs will launch the background processing task.
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

# GET endpoint: retrieve scores
@app.route('/api/scores', methods=['GET'])
async def get_scores():
    date_filter = request.args.get('date')
    game_id_filter = request.args.get('gameId')
    condition = {}
    if game_id_filter:
        condition["gameId"] = game_id_filter
    if date_filter:
        # For prototype, assume timestamp starts with the given date string.
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

# POST endpoint: create subscription
# NOTE: Workaround for quart-schema issue: for POST requests, route decorator goes first, then validation.
@app.route('/api/subscriptions', methods=['POST'])
@validate_request(SubscriptionRequest)  # Added second per workaround for post requests
async def create_subscription(data: SubscriptionRequest):
    email = data.email
    filters = {
        "team": data.team,
        "gameType": data.gameType
    }

    if not email:
        return jsonify({"status": "error", "message": "Email is required"}), 400

    sub_data = {
        "email": email,
        "filters": filters,
        "createdAt": datetime.datetime.utcnow().isoformat() + "Z"
    }
    try:
        # Persist the subscription entity applying its workflow before saving.
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

# GET endpoint: list subscriptions
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