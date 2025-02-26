from common.grpc_client.grpc_client import grpc_stream
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

# Startup hook to initialize cyoda.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task
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