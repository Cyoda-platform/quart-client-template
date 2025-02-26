from dataclasses import dataclass
import asyncio
import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

app = Quart(__name__)
QuartSchema(app)  # Register QuartSchema

# Workflow function for "job" entity.
# This function is applied asynchronously before persisting the job entity.
# It performs external API calls, notifies subscribers, and updates the job state.
async def process_job(job_entity: dict):
    # Avoid calling add/update/delete on the same job entity.
    # Capture triggerTime from the job entity.
    trigger_time = job_entity.get("triggerTime", "unknown")
    
    # Perform an external API call for fetching game scores.
    external_url = (
        "https://api.sportsdata.io/v3/nba/scores/ScoresBasic/2020-SEP-01"
        "?key=YOUR_API_KEY"  # TODO: Replace with an actual API key.
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(external_url) as response:
                external_data = await response.json()
    except Exception as e:
        # Log the error and define fallback data.
        print(f"Error fetching data from external API in process_job: {e}")
        external_data = {"updatedGames": []}

    # Process external data; here we simulate the result.
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
    
    # Update the "score" entity with the new results.
    # This is allowed since "score" is a different entity_model.
    try:
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="score",
            entity_version=ENTITY_VERSION,
            entity=result,
            meta={"technical_id": "latest"}
        )
    except Exception as e:
        print(f"Error updating score entity in process_job: {e}")
    
    # Retrieve all subscribers to notify them.
    try:
        subscribers = await entity_service.get_items(
            token=cyoda_token,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        print(f"Error retrieving subscribers in process_job: {e}")
        subscribers = []
    
    # Simulate notification to each subscriber.
    for sub in subscribers:
        try:
            print(f"Notify subscriber at {sub.get('callbackUrl')} with data: {result}")
            # In production, perform an asynchronous POST to sub['callbackUrl'].
        except Exception as e:
            print(f"Error notifying subscriber {sub.get('callbackUrl')}: {e}")
    
    # Modify the job entity state directly.
    job_entity["status"] = "completed"
    job_entity["processedAt"] = trigger_time  # Record processing time (for illustration).
    return job_entity

# Workflow function for "subscriber" entity.
# This function preprocesses and normalizes the subscriber data before persistence.
async def process_subscriber(subscriber_entity: dict):
    if "subscriptionType" in subscriber_entity and isinstance(subscriber_entity["subscriptionType"], str):
        subscriber_entity["subscriptionType"] = subscriber_entity["subscriptionType"].lower()
    if "callbackUrl" in subscriber_entity and isinstance(subscriber_entity["callbackUrl"], str):
        subscriber_entity["callbackUrl"] = subscriber_entity["callbackUrl"].strip()
    return subscriber_entity

# Startup hook to initialize cyoda.
@app.before_serving
async def startup():
    try:
        await init_cyoda(cyoda_token)
    except Exception as e:
        print(f"Error during startup initialization: {e}")

# Data classes for request validation.
@dataclass
class IngestRequest:
    triggerTime: str  # Use only primitive types; add additional fields if needed.

@dataclass
class SubscribeRequest:
    callbackUrl: str
    subscriptionType: str  # e.g., "scoreUpdates"

@dataclass
class UnsubscribeRequest:
    callbackUrl: str

# POST endpoint: Ingest.
# This endpoint creates a job entity that will be processed by its workflow function.
@app.route('/nba/ingest', methods=['POST'])
@validate_request(IngestRequest)
async def ingest(data: IngestRequest):
    # Prepare job data with an initial status.
    job_data = {"triggerTime": data.triggerTime, "status": "processing"}
    try:
        # The process_job workflow will be applied before persisting the job entity.
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            entity=job_data,
            workflow=process_job
        )
    except Exception as e:
        print(f"Error adding job entity: {e}")
        return jsonify({"status": "error", "message": "Failed to trigger ingestion."}), 500
    return jsonify({
        "status": "accepted",
        "jobId": job_id,
        "message": "Ingestion triggered."
    })

# GET endpoint: Retrieve scores.
@app.route('/nba/scores', methods=['GET'])
async def get_scores():
    try:
        score = await entity_service.get_item(
            token=cyoda_token,
            entity_model="score",
            entity_version=ENTITY_VERSION,
            technical_id="latest"
        )
    except Exception as e:
        print(f"Error retrieving score entity: {e}")
        score = {"updatedGames": []}
    return jsonify({
        "status": "ok",
        "latestScores": score.get("updatedGames", [])
    })

# POST endpoint for subscription.
# This endpoint creates a subscriber entity processed by its workflow function.
@app.route('/nba/subscribe', methods=['POST'])
@validate_request(SubscribeRequest)
async def subscribe(data: SubscribeRequest):
    if not data.callbackUrl:
        return jsonify({"status": "error", "message": "Missing callbackUrl"}), 400
    subscriber_data = {"callbackUrl": data.callbackUrl, "subscriptionType": data.subscriptionType}
    try:
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
            entity=subscriber_data,
            workflow=process_subscriber
        )
    except Exception as e:
        print(f"Error adding subscriber entity: {e}")
        return jsonify({"status": "error", "message": "Subscription failed."}), 500
    return jsonify({
        "status": "success",
        "message": "Subscribed successfully."
    })

# DELETE endpoint for unsubscription.
@app.route('/nba/unsubscribe', methods=['DELETE'])
@validate_request(UnsubscribeRequest)
async def unsubscribe(data: UnsubscribeRequest):
    if not data.callbackUrl:
        return jsonify({"status": "error", "message": "Missing callbackUrl"}), 400
    try:
        subscribers = await entity_service.get_items_by_condition(
            token=cyoda_token,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
            condition={"callbackUrl": data.callbackUrl}
        )
    except Exception as e:
        print(f"Error retrieving subscribers for unsubscription: {e}")
        return jsonify({"status": "error", "message": "Failed to retrieve subscribers."}), 500
    for sub in subscribers:
        try:
            await entity_service.delete_item(
                token=cyoda_token,
                entity_model="subscriber",
                entity_version=ENTITY_VERSION,
                entity=sub,
                meta={}
            )
        except Exception as e:
            print(f"Error deleting subscriber entity: {e}")
    return jsonify({
        "status": "success",
        "message": "Unsubscribed successfully."
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)