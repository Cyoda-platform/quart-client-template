import asyncio
import datetime
import uuid
import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

app = Quart(__name__)
QuartSchema(app)  # Schema integration for request/response validation (data is dynamic)

# Global in-memory caches (mock persistence)
scores_cache = {}         # key: gameId, value: score data
subscriptions_cache = {}  # key: subscriptionId, value: subscription details
jobs_cache = {}           # key: job_id, value: job status info

SPORTS_DATA_API_KEY = "f8824354d80d45368063dd2e6fb16c38"
SPORTS_DATA_URL_TEMPLATE = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=" + SPORTS_DATA_API_KEY

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

# Background processing function for score ingestion
async def process_scores(job_id: str, date: str):
    job = jobs_cache[job_id]
    requested_at = job["requestedAt"]
    external_data = await fetch_scores_from_external(date)
    
    if external_data is None:
        jobs_cache[job_id]["status"] = "failed"
        return

    # TODO: Implement proper change detection logic based on requirements
    # For prototype, assume all fetched data triggers an update event.
    updated_games = []
    for game in external_data:
        game_id = game.get("GameID", str(uuid.uuid4()))  # Using external id if available
        previous_record = scores_cache.get(game_id)
        
        # Simple change detection: if no previous record or score changes, update the cache.
        if not previous_record or previous_record.get("finalScore") != game.get("FinalScore"):
            scores_cache[game_id] = {
                "gameId": game_id,
                "homeTeam": game.get("HomeTeam"),
                "awayTeam": game.get("AwayTeam"),
                "quarterScores": game.get("QuarterScores", []),
                "finalScore": game.get("FinalScore"),
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
            }
            updated_games.append(scores_cache[game_id])
            # TODO: Publish event to internal message bus for notification delivery

    jobs_cache[job_id]["status"] = "completed"
    jobs_cache[job_id]["completedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
    # For prototype, printing the events as a mock of event publication
    if updated_games:
        print(f"Job {job_id} - Score updates detected and events published: {updated_games}")

@app.route('/api/scores/fetch-real-time', methods=['POST'])
async def fetch_real_time_scores():
    req_data = await request.get_json()
    date = req_data.get("date")
    if not date:
        return jsonify({"status": "error", "message": "Missing required field: date"}), 400

    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat() + "Z"
    jobs_cache[job_id] = {"status": "processing", "requestedAt": requested_at}

    # Fire and forget the processing task.
    asyncio.create_task(process_scores(job_id, date))

    return jsonify({
        "status": "success",
        "message": "Scores fetch initiated",
        "jobId": job_id,
        "requestedAt": requested_at
    })

@app.route('/api/scores', methods=['GET'])
async def get_scores():
    # Retrieve query parameters if any
    date_filter = request.args.get('date')
    game_id_filter = request.args.get('gameId')
    results = list(scores_cache.values())
    
    # TODO: For prototype only simple filtering is implemented.
    if game_id_filter:
        results = [game for game in results if game.get("gameId") == game_id_filter]
    if date_filter:
        results = [game for game in results if game.get("timestamp", "").startswith(date_filter)]
    
    return jsonify({
        "status": "success",
        "results": results
    })

@app.route('/api/subscriptions', methods=['POST'])
async def create_subscription():
    req_data = await request.get_json()
    email = req_data.get("email")
    filters = req_data.get("filters", {})

    if not email:
        return jsonify({"status": "error", "message": "Email is required"}), 400

    subscription_id = str(uuid.uuid4())
    subscriptions_cache[subscription_id] = {
        "subscriptionId": subscription_id,
        "email": email,
        "filters": filters,
        "createdAt": datetime.datetime.utcnow().isoformat() + "Z"
    }

    # TODO: In a full implementation, validate email and handle duplicate subscriptions.
    return jsonify({
        "status": "success",
        "message": "Subscription created successfully",
        "subscriptionId": subscription_id
    })

@app.route('/api/subscriptions', methods=['GET'])
async def list_subscriptions():
    results = list(subscriptions_cache.values())
    return jsonify({
        "status": "success",
        "subscriptions": results
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)