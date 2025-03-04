from common.grpc_client.grpc_client import grpc_stream
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

# Startup routine: initialize cyoda before serving requests.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

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

    filters = {}
    if data.team.strip():
        filters["team"] = data.team.strip()
    if data.gameType.strip():
        filters["gameType"] = data.gameType.strip()

    sub_data = {
        "email": email,
        "createdAt": datetime.datetime.utcnow().isoformat() + "Z"
    }
    if filters:
        sub_data["filters"] = filters

    try:
        subscription_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="subscriptions",
            entity_version=ENTITY_VERSION,
            entity=sub_data,
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