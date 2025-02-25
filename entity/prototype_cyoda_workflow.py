import asyncio
import uuid
import datetime
import aiohttp
from dataclasses import dataclass

from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

# Import external service and config constants.
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service
from common.config.config import ENTITY_VERSION

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

JOBS = {}  # Dictionary to hold job statuses.
EXTERNAL_API_URL = "https://api.practicesoftwaretesting.com/brands"

# Workflow function applied to the entity before persistence.
# This function supports asynchronous operations such as firing off auxiliary tasks
# and modifying the entity state directly. Any async task that does not interfere
# with current entity persistence (e.g. retrieving supplementary data from another source)
# can be handled here.
async def process_brands(entity_data):
    # Ensure entity_data is a dict.
    if not isinstance(entity_data, dict):
        return entity_data

    # Asynchronous function to fetch supplementary data.
    async def fetch_supplementary():
        try:
            async with aiohttp.ClientSession() as session:
                # Example URL fetching supplementary data from a different source.
                async with session.get("https://api.example.com/supplementary_data", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        supplementary = await resp.json()
                        # Add supplementary data to entity_data.
                        entity_data["supplementary"] = supplementary
                    else:
                        # Record error information if needed.
                        entity_data["supplementary_error"] = f"Unexpected status: {resp.status}"
        except Exception as err:
            # Prevent exception from affecting the workflow; log error in entity_data.
            entity_data["supplementary_error"] = str(err)

    # Launch fire-and-forget task to fetch supplementary data.
    asyncio.create_task(fetch_supplementary())

    # Modify the entity state with additional metadata.
    entity_data["processedAt"] = datetime.datetime.utcnow().isoformat()
    # Additional processing logic can be added here.
    return entity_data

# Startup hook to initialize the external service.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@dataclass
class UpdateRequest:
    fetchTimeout: int = 5000
    forceUpdate: bool = False

# This function encapsulates fetching data from the external API,
# applying the workflow transformation, and sending the entity with the new state
# to the external entity service.
async def process_entity(job, options):
    fetch_timeout_ms = options.get("fetchTimeout", 5000)
    timeout_secs = fetch_timeout_ms / 1000

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout_secs)) as session:
            async with session.get(EXTERNAL_API_URL, headers={"accept": "application/json"}) as response:
                if response.status == 200:
                    response_data = await response.json()
                    # Apply workflow function asynchronously before persisting the entity.
                    external_id = await entity_service.add_item(
                        token=cyoda_token,
                        entity_model="brands",
                        entity_version=ENTITY_VERSION,  # always use this constant
                        entity=response_data,  # the original fetched data
                        workflow=process_brands  # Workflow function applied to transform entity.
                    )
                    job["status"] = "completed"
                    job["completedAt"] = datetime.datetime.utcnow().isoformat()
                    return external_id
                else:
                    job["status"] = "error"
                    job["error"] = f"Received unexpected status: {response.status}"
                    return None
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
        return None

# POST endpoint to update brand data.
# This endpoint delegates all non-controller logic to the process_entity and workflow functions.
@app.route('/api/brands/update', methods=['POST'])
@validate_request(UpdateRequest)
async def update_brands(data: UpdateRequest):
    job_id = str(uuid.uuid4())
    job = {
        "id": job_id,
        "status": "processing",
        "requestedAt": datetime.datetime.utcnow().isoformat()
    }
    JOBS[job_id] = job

    # Process the job which fetches, transforms, and persists the entity.
    result = await asyncio.create_task(process_entity(job, data.__dict__))

    if result is not None:
        return jsonify({
            "status": "success",
            "data": result,  # External service ID.
            "message": "Brand data successfully updated via external service.",
            "jobId": job_id
        }), 200
    else:
        return jsonify({
            "status": "error",
            "message": "Failed to fetch/update brand data.",
            "jobId": job_id,
            "details": job.get("error", "Unknown error")
        }), 500

# GET endpoint to retrieve brand data from the external service.
@app.route('/api/brands', methods=['GET'])
async def get_brands():
    result = await entity_service.get_items(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION
    )
    if result:
        return jsonify({
            "status": "success",
            "data": result
        }), 200
    else:
        return jsonify({
            "status": "error",
            "message": "No brand data available. Please update the data by sending a POST request."
        }), 404

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)