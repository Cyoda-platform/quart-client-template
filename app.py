from common.grpc_client.grpc_client import grpc_stream
import asyncio
import json
import uuid
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Dummy external API URL (TODO: Replace with actual SportsData API URL and parameters)
EXTERNAL_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/GamesByDate/2023-OCT-10"
API_KEY = "YOUR_API_KEY"  # TODO: Replace with your API key for SportsData

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

# Dataclasses for request validation
@dataclass
class ScoreConfig:
    interval: int
    date: Optional[str] = None

@dataclass
class ScoreFetchRequest:
    fetchMode: str
    config: ScoreConfig

@dataclass
class SubscriptionRequest:
    email: str
    preferences: List[str]

async def fetch_external_scores():
    # Fetch scores from the external API using aiohttp.ClientSession.
    async with aiohttp.ClientSession() as session:
        headers = {"Ocp-Apim-Subscription-Key": API_KEY}
        async with session.get(EXTERNAL_API_URL, headers=headers) as response:
            if response.status != 200:
                # Handle non-200 responses
                raise Exception("Failed to fetch external scores, status code: " + str(response.status))
            data = await response.json()
            return data  # Expecting data to be a list of game objects

async def process_scores(data):
    """
    Process the fetched external scores.
    For each game, check if it exists in the external repository.
    If not or if significant changes are detected, add or update the game record.
    All asynchronous tasks (like sending notifications) are decoupled via workflow.
    """
    updated_games = []
    for game in data:
        game_id = game.get("GameID")
        if game_id is None:
            continue

        # Build a new record from the external data
        new_record = {
            "gameId": game_id,
            "awayTeam": game.get("AwayTeam"),
            "homeTeam": game.get("HomeTeam"),
            "awayTeamScore": game.get("AwayTeamScore"),
            "homeTeamScore": game.get("HomeTeamScore"),
            "Status": game.get("Status"),
            "updatedAt": datetime.utcnow().isoformat() + "Z"
        }
        significant_change = False
        try:
            existing = await entity_service.get_item(
                token=cyoda_token,
                entity_model="scores",
                entity_version=ENTITY_VERSION,
                technical_id=game_id
            )
        except Exception:
            existing = None

        if not existing:
            # New game record, mark as event triggered.
            new_record["eventTriggered"] = True
            # Persist new record with workflow processing
            await entity_service.add_item(
                token=cyoda_token,
                entity_model="scores",
                entity_version=ENTITY_VERSION,
                entity=new_record,
                )
            significant_change = True
        else:
            # Check for significant changes comparing record fields
            if (game.get("AwayTeamScore") != existing.get("awayTeamScore") or
                game.get("HomeTeamScore") != existing.get("homeTeamScore") or
                game.get("Status") != existing.get("Status")):
                new_record["eventTriggered"] = True
                # Update existing record; update_item may not support workflow so workflow is applied only on add.
                await entity_service.update_item(
                    token=cyoda_token,
                    entity_model="scores",
                    entity_version=ENTITY_VERSION,
                    entity=new_record,
                    meta={}
                )
                significant_change = True

        if significant_change:
            updated_games.append(new_record)
    return updated_games

# POST endpoint: Triggers external data retrieval and processing.
@app.route("/api/v1/scores/fetch", methods=["POST"])
@validate_request(ScoreFetchRequest)
async def fetch_scores(data: ScoreFetchRequest):
    """
    POST /api/v1/scores/fetch
    Triggers external data retrieval, processes scores data,
    and fires off notifications via workflow logic.
    """
    try:
        external_data = await fetch_external_scores()
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    updated_games = await process_scores(external_data)
    response = {
        "status": "success",
        "updatedGames": updated_games
    }
    return jsonify(response)

# GET endpoint for scores: Retrieves scores.
@app.route("/api/v1/scores", methods=["GET"])
async def get_scores():
    """
    GET /api/v1/scores
    Retrieves current NBA game score data.
    """
    try:
        scores = await entity_service.get_items(
            token=cyoda_token,
            entity_model="scores",
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        return jsonify({"message": str(e)}), 500
    return jsonify(scores)

# POST endpoint: Creates a subscription.
@app.route("/api/v1/subscriptions", methods=["POST"])
@validate_request(SubscriptionRequest)
async def create_subscription(data: SubscriptionRequest):
    """
    POST /api/v1/subscriptions
    Creates a new subscription for email notifications.
    """
    if not data.email:
        return jsonify({"message": "Email is required"}), 400

    subscription = {
        "email": data.email,
        "preferences": data.preferences,
        "createdAt": datetime.utcnow().isoformat() + "Z"
    }
    try:
        subscription_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="subscriptions",
            entity_version=ENTITY_VERSION,
            entity=subscription,
            )
    except Exception as e:
        return jsonify({"message": str(e)}), 500

    return jsonify({"subscriptionId": subscription_id, "message": "Subscription created successfully."})

# GET endpoint: Retrieves subscriptions.
@app.route("/api/v1/subscriptions", methods=["GET"])
async def get_subscriptions():
    """
    GET /api/v1/subscriptions
    Retrieves a list of active subscriptions.
    """
    try:
        subscriptions = await entity_service.get_items(
            token=cyoda_token,
            entity_model="subscriptions",
            entity_version=ENTITY_VERSION
        )
    except Exception as e:
        return jsonify({"message": str(e)}), 500
    return jsonify(subscriptions)

# PUT endpoint: Updates a subscription.
@app.route("/api/v1/subscriptions/<subscription_id>", methods=["PUT"])
@validate_request(SubscriptionRequest)
async def update_subscription(data: SubscriptionRequest, subscription_id):
    """
    PUT /api/v1/subscriptions/{subscriptionId}
    Updates subscription details.
    """
    try:
        existing = await entity_service.get_item(
            token=cyoda_token,
            entity_model="subscriptions",
            entity_version=ENTITY_VERSION,
            technical_id=subscription_id
        )
    except Exception:
        existing = None

    if not existing:
        return jsonify({"message": "Subscription not found"}), 404

    updated_subscription = existing.copy()
    if data.email:
        updated_subscription["email"] = data.email
    if data.preferences is not None:
        updated_subscription["preferences"] = data.preferences
    updated_subscription["updatedAt"] = datetime.utcnow().isoformat() + "Z"

    try:
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="subscriptions",
            entity_version=ENTITY_VERSION,
            entity=updated_subscription,
            meta={}
        )
    except Exception as e:
        return jsonify({"message": str(e)}), 500

    return jsonify({"subscriptionId": subscription_id, "message": "Subscription updated successfully."})

# DELETE endpoint: Deletes a subscription.
@app.route("/api/v1/subscriptions/<subscription_id>", methods=["DELETE"])
async def delete_subscription(subscription_id):
    """
    DELETE /api/v1/subscriptions/{subscriptionId}
    Deletes an existing subscription.
    """
    try:
        existing = await entity_service.get_item(
            token=cyoda_token,
            entity_model="subscriptions",
            entity_version=ENTITY_VERSION,
            technical_id=subscription_id
        )
    except Exception:
        existing = None

    if not existing:
        return jsonify({"message": "Subscription not found"}), 404

    try:
        await entity_service.delete_item(
            token=cyoda_token,
            entity_model="subscriptions",
            entity_version=ENTITY_VERSION,
            entity=existing,
            meta={}
        )
    except Exception as e:
        return jsonify({"message": str(e)}), 500

    return jsonify({"subscriptionId": subscription_id, "message": "Subscription deleted successfully."})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)