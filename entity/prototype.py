import asyncio
import aiohttp
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

app = Quart(__name__)
QuartSchema(app)  # Register QuartSchema

# Data classes for validation
@dataclass
class IngestRequest:
    triggerTime: str  # use only primitive types; TODO: Add additional fields if needed

@dataclass
class SubscribeRequest:
    callbackUrl: str
    subscriptionType: str  # e.g., "scoreUpdates"

@dataclass
class UnsubscribeRequest:
    callbackUrl: str

# In-memory caches and storage for prototype purposes.
scores_cache = {}  # To store the latest scores; key "latest" holds the result.
subscribers = []   # List of subscriber dicts: {"callbackUrl": ..., "subscriptionType": ...}
jobs = {}          # To track ingestion jobs.

# Asynchronous processing task for ingestion.
async def process_entity(job_id: str, requested_at: str, data: dict):
    # TODO: Customize external API call parameters based on real requirements.
    # For now, use a mock/fixed URL with a placeholder API key.
    external_url = (
        "https://api.sportsdata.io/v3/nba/scores/ScoresBasic/2020-SEP-01"
        "?key=YOUR_API_KEY"  # TODO: Replace YOUR_API_KEY with actual API key.
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(external_url) as response:
                # TODO: Handle non-200 responses and error conditions.
                external_data = await response.json()
    except Exception as e:
        # TODO: Improve error handling here.
        print(f"Error fetching data from external API: {e}")
        external_data = {"updatedGames": []}

    # TODO: Process external_data and perform change detection.
    # Use a mock processing result here as a placeholder.
    result = {
        "updatedGames": [
            {
                "gameId": "1234",
                "homeTeam": "Team A",
                "awayTeam": "Team B",
                "homeScore": 101,
                "awayScore": 99,
                "timeRemaining": "02:15"
            }
        ]
    }
    # Update the in-memory scores cache
    scores_cache["latest"] = result

    # TODO: Publish events to subscribers. For now, simulate notification by printing.
    for sub in subscribers:
        # In a robust solution, we would POST to the subscriber's callbackUrl.
        print(f"Notify subscriber at {sub['callbackUrl']} with data: {result}")
        # Example: Uncomment the code below once a proper HTTP notification mechanism is in place.
        # async with aiohttp.ClientSession() as session:
        #     await session.post(sub['callbackUrl'], json=result)

    jobs[job_id]["status"] = "completed"


# POST endpoint: Route decorator comes first, then validate_request decorator (workaround for quart-schema issue)
@app.route('/nba/ingest', methods=['POST'])
@validate_request(IngestRequest)  # For POST, place validate_request after route decorator
async def ingest(data: IngestRequest):
    # data is validated and available as IngestRequest instance
    requested_at = data.triggerTime if data.triggerTime else "unknown"
    job_id = f"job_{len(jobs) + 1}"
    jobs[job_id] = {"status": "processing", "requestedAt": requested_at}
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, requested_at, request.json))
    return jsonify({
        "status": "accepted",
        "jobId": job_id,
        "message": "Ingestion triggered."
    })


# GET endpoint without parameters; no request validation needed.
@app.route('/nba/scores', methods=['GET'])
async def get_scores():
    result = scores_cache.get("latest", {"updatedGames": []})
    return jsonify({
        "status": "ok",
        "latestScores": result.get("updatedGames")
    })


# POST endpoint for subscription.
@app.route('/nba/subscribe', methods=['POST'])
@validate_request(SubscribeRequest)  # For POST, validate_request comes after route decorator.
async def subscribe(data: SubscribeRequest):
    callback_url = data.callbackUrl
    if not callback_url:
        return jsonify({"status": "error", "message": "Missing callbackUrl"}), 400
    # TODO: Validate the callbackUrl format.
    subscribers.append({
        "callbackUrl": callback_url,
        "subscriptionType": data.subscriptionType
    })
    return jsonify({
        "status": "success",
        "message": "Subscribed successfully."
    })


# DELETE endpoint for unsubscription.
@app.route('/nba/unsubscribe', methods=['DELETE'])
@validate_request(UnsubscribeRequest)  # For DELETE (with body), using validate_request similarly.
async def unsubscribe(data: UnsubscribeRequest):
    callback_url = data.callbackUrl
    if not callback_url:
        return jsonify({"status": "error", "message": "Missing callbackUrl"}), 400
    global subscribers
    subscribers = [sub for sub in subscribers if sub.get("callbackUrl") != callback_url]
    return jsonify({
        "status": "success",
        "message": "Unsubscribed successfully."
    })


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)