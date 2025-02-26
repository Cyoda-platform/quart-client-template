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

# Workflow function for "job" entity
async def process_job(entity: dict):
    # Example workflow: mark entity as processed
    entity["workflowApplied"] = True
    return entity

# Workflow function for "subscriber" entity
async def process_subscriber(entity: dict):
    # Example workflow: normalize subscription type and callbackUrl
    if "subscriptionType" in entity:
        entity["subscriptionType"] = entity["subscriptionType"].lower()
    if "callbackUrl" in entity:
        entity["callbackUrl"] = entity["callbackUrl"].strip()
    return entity

# Startup hook to initialize cyoda
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

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

# Asynchronous processing task for ingestion.
async def process_entity(job_id: str, requested_at: str, data: dict):
    # Call external API (using a mock/fixed URL; adjust as needed)
    external_url = (
        "https://api.sportsdata.io/v3/nba/scores/ScoresBasic/2020-SEP-01"
        "?key=YOUR_API_KEY"  # TODO: Replace with an actual API key
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(external_url) as response:
                external_data = await response.json()
    except Exception as e:
        # Error handling for external API call
        print(f"Error fetching data from external API: {e}")
        external_data = {"updatedGames": []}
    
    # Process external_data and prepare result
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
    # Update the "score" entity with the latest result; using technical_id "latest"
    await entity_service.update_item(
        token=cyoda_token,
        entity_model="score",
        entity_version=ENTITY_VERSION,
        entity=result,
        meta={"technical_id": "latest"}
    )
    
    # Retrieve all subscribers from the external service
    subscribers = await entity_service.get_items(
        token=cyoda_token,
        entity_model="subscriber",
        entity_version=ENTITY_VERSION,
    )
    # Publish events to subscribers (simulate notification)
    for sub in subscribers:
        print(f"Notify subscriber at {sub.get('callbackUrl')} with data: {result}")
        # In a robust solution, we would POST to the subscriber's callbackUrl.
    
    # Update the "job" entity status to completed using its technical_id (job_id)
    await entity_service.update_item(
        token=cyoda_token,
        entity_model="job",
        entity_version=ENTITY_VERSION,
        entity={"status": "completed"},
        meta={"technical_id": job_id}
    )

# POST endpoint: Ingest - triggers background processing
@app.route('/nba/ingest', methods=['POST'])
@validate_request(IngestRequest)
async def ingest(data: IngestRequest):
    requested_at = data.triggerTime if data.triggerTime else "unknown"
    # Instead of local cache, add a job via external entity_service
    job_data = {"triggerTime": data.triggerTime, "status": "processing"}
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="job",
        entity_version=ENTITY_VERSION,
        entity=job_data,
        workflow=process_job  # Workflow function applied to the job entity
    )
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, requested_at, await request.get_json()))
    return jsonify({
        "status": "accepted",
        "jobId": job_id,
        "message": "Ingestion triggered."
    })

# GET endpoint: Retrieve scores
@app.route('/nba/scores', methods=['GET'])
async def get_scores():
    try:
        score = await entity_service.get_item(
            token=cyoda_token,
            entity_model="score",
            entity_version=ENTITY_VERSION,
            technical_id="latest"
        )
    except Exception:
        score = {"updatedGames": []}
    return jsonify({
        "status": "ok",
        "latestScores": score.get("updatedGames", [])
    })

# POST endpoint for subscription.
@app.route('/nba/subscribe', methods=['POST'])
@validate_request(SubscribeRequest)
async def subscribe(data: SubscribeRequest):
    callback_url = data.callbackUrl
    if not callback_url:
        return jsonify({"status": "error", "message": "Missing callbackUrl"}), 400
    # Add subscriber via external entity_service
    subscriber_data = {"callbackUrl": callback_url, "subscriptionType": data.subscriptionType}
    await entity_service.add_item(
        token=cyoda_token,
        entity_model="subscriber",
        entity_version=ENTITY_VERSION,
        entity=subscriber_data,
        workflow=process_subscriber  # Workflow function applied to the subscriber entity
    )
    return jsonify({
        "status": "success",
        "message": "Subscribed successfully."
    })

# DELETE endpoint for unsubscription.
@app.route('/nba/unsubscribe', methods=['DELETE'])
@validate_request(UnsubscribeRequest)
async def unsubscribe(data: UnsubscribeRequest):
    callback_url = data.callbackUrl
    if not callback_url:
        return jsonify({"status": "error", "message": "Missing callbackUrl"}), 400
    # Retrieve subscribers matching the callbackUrl condition.
    subscribers = await entity_service.get_items_by_condition(
        token=cyoda_token,
        entity_model="subscriber",
        entity_version=ENTITY_VERSION,
        condition={"callbackUrl": callback_url}
    )
    # Delete each matching subscriber.
    for sub in subscribers:
        await entity_service.delete_item(
            token=cyoda_token,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
            entity=sub,
            meta={}
        )
    return jsonify({
        "status": "success",
        "message": "Unsubscribed successfully."
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)