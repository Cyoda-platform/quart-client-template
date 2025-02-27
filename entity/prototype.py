import asyncio
import json
import uuid
from datetime import datetime

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# In-memory caches for persistence
scores_cache = {}         # Key: gameId, Value: game score details
subscriptions_cache = {}  # Key: subscriptionId, Value: subscription details

# Dummy external API URL (TODO: Replace with actual SportsData API URL and parameters)
EXTERNAL_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/GamesByDate/2023-OCT-10"
API_KEY = "YOUR_API_KEY"  # TODO: Replace with your API key for SportsData


async def fetch_external_scores():
    """Fetch scores from the external API using aiohttp.ClientSession."""
    async with aiohttp.ClientSession() as session:
        # TODO: Adjust request method and parameters as required by the external SportsData API.
        headers = {"Ocp-Apim-Subscription-Key": API_KEY}
        async with session.get(EXTERNAL_API_URL, headers=headers) as response:
            if response.status != 200:
                # TODO: Implement better error handling and retry logic.
                raise Exception("Failed to fetch external scores")
            data = await response.json()
            return data  # Expecting data to be a list of game objects


async def process_scores(data):
    """
    Process the fetched external scores.
    Compare with the stored scores_cache to detect significant changes,
    and update the cache. Trigger email notifications for significant changes.
    """
    updated_games = []
    # Iterate through the list of games from the external source
    for game in data:
        # Use gameId as the unique identifier. Adjust if necessary.
        game_id = game.get("GameID")
        if game_id is None:
            continue

        current_score = scores_cache.get(game_id)
        # Simple significant change logic: if the score changes or status changes.
        is_significant = False
        if not current_score:
            is_significant = True  # New game record
        else:
            # Check if away or home score changed OR status changed
            if (game.get("AwayTeamScore") != current_score.get("AwayTeamScore") or
                game.get("HomeTeamScore") != current_score.get("HomeTeamScore") or
                game.get("Status") != current_score.get("Status")):
                is_significant = True

        # Update cache with the latest game data
        scores_cache[game_id] = {
            "gameId": game_id,
            "awayTeam": game.get("AwayTeam"),
            "homeTeam": game.get("HomeTeam"),
            "awayTeamScore": game.get("AwayTeamScore"),
            "homeTeamScore": game.get("HomeTeamScore"),
            "Status": game.get("Status"),
            "updatedAt": datetime.utcnow().isoformat() + "Z"
        }

        if is_significant:
            updated_game = scores_cache[game_id]
            updated_game["eventTriggered"] = True
            updated_games.append(updated_game)
            # TODO: Implement actual email notification sending to subscribers.
            print(f"Trigger notification for game {game_id} update.")
    return updated_games


@app.route("/api/v1/scores/fetch", methods=["POST"])
async def fetch_scores():
    """
    POST /api/v1/scores/fetch
    Triggers the external data retrieval, processes the scores,
    updates the internal cache, and triggers event notifications.
    """
    req_data = await request.get_json()
    fetch_mode = req_data.get("fetchMode", "manual")
    config = req_data.get("config", {})
    interval = config.get("interval", 60)
    date_filter = config.get("date", None)  # Currently unused in mock, TODO: Implement filtering by date

    # Fire and forget the processing task.
    try:
        # Fetch external scores (using a placeholder call)
        external_data = await fetch_external_scores()
    except Exception as e:
        # TODO: Implement retry mechanism and proper error logging
        return jsonify({"status": "error", "message": str(e)}), 500

    # Process scores in background task
    updated_games = await process_scores(external_data)
    response = {
        "status": "success",
        "updatedGames": updated_games
    }
    return jsonify(response)


@app.route("/api/v1/scores", methods=["GET"])
async def get_scores():
    """
    GET /api/v1/scores
    Retrieves the current NBA game score data from the in-memory cache.
    """
    return jsonify(list(scores_cache.values()))


@app.route("/api/v1/subscriptions", methods=["POST"])
async def create_subscription():
    """
    POST /api/v1/subscriptions
    Creates a new subscription for receiving email notifications.
    """
    data = await request.get_json()
    email = data.get("email")
    preferences = data.get("preferences", [])
    if not email:
        return jsonify({"message": "Email is required"}), 400

    subscription_id = str(uuid.uuid4())
    subscription = {
        "subscriptionId": subscription_id,
        "email": email,
        "preferences": preferences,
        "createdAt": datetime.utcnow().isoformat() + "Z"
    }
    subscriptions_cache[subscription_id] = subscription
    return jsonify({"subscriptionId": subscription_id, "message": "Subscription created successfully."})


@app.route("/api/v1/subscriptions", methods=["GET"])
async def get_subscriptions():
    """
    GET /api/v1/subscriptions
    Retrieve a list of active subscriptions.
    """
    return jsonify(list(subscriptions_cache.values()))


@app.route("/api/v1/subscriptions/<subscription_id>", methods=["PUT"])
async def update_subscription(subscription_id):
    """
    PUT /api/v1/subscriptions/{subscriptionId}
    Updates the subscription details.
    """
    if subscription_id not in subscriptions_cache:
        return jsonify({"message": "Subscription not found"}), 404

    data = await request.get_json()
    email = data.get("email")
    preferences = data.get("preferences")
    if email:
        subscriptions_cache[subscription_id]["email"] = email
    if preferences is not None:
        subscriptions_cache[subscription_id]["preferences"] = preferences
    return jsonify({"subscriptionId": subscription_id, "message": "Subscription updated successfully."})


@app.route("/api/v1/subscriptions/<subscription_id>", methods=["DELETE"])
async def delete_subscription(subscription_id):
    """
    DELETE /api/v1/subscriptions/{subscriptionId}
    Deletes an existing subscription.
    """
    if subscription_id not in subscriptions_cache:
        return jsonify({"message": "Subscription not found"}), 404

    del subscriptions_cache[subscription_id]
    return jsonify({"subscriptionId": subscription_id, "message": "Subscription deleted successfully."})


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)