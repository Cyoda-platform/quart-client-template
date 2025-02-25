import asyncio
import uuid
import datetime
import aiohttp
from dataclasses import dataclass

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

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
# and modifying the entity state directly. Any async task that does not affect the current
# entity persistence (e.g. retrieving supplementary data) can be handled here.
async def process_brands(entity_data):
    # Fire and forget asynchronous task to fetch supplementary data.
    async def fetch_supplementary():
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.example.com/supplementary_data") as resp:
                    if resp.status == 200:
                        supplementary = await resp.json()
                        # Directly modify the entity state with the supplementary data.
                        entity_data["supplementary"] = supplementary
        except Exception as e:
            # Log error or handle accordingly.
            entity_data["supplementary_error"] = str(e)

    # Launch the supplementary data fetch without awaiting it.
    asyncio.create_task(fetch_supplementary())

    # Modify the entity state with additional metadata.
    entity_data["processedAt"] = datetime.datetime.utcnow().isoformat()
    # You may add further transformation or async tasks here.
    return entity_data

# Startup hook to initialize cyoda.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@dataclass
class UpdateRequest:
    fetchTimeout: int = 5000
    forceUpdate: bool = False

async def process_entity(job, options):
    """
    Process the job: fetch data from the external API, 
    send the retrieved data to the external entity service with the workflow transformation,
    and update the job status.
    """
    fetch_timeout_ms = options.get("fetchTimeout", 5000)
    timeout_secs = fetch_timeout_ms / 1000

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout_secs)) as session:
            async with session.get(EXTERNAL_API_URL, headers={"accept": "application/json"}) as response:
                if response.status == 200:
                    response_data = await response.json()
                    # Send data to the external service with workflow function applied.
                    external_id = await entity_service.add_item(
                        token=cyoda_token,
                        entity_model="brands",
                        entity_version=ENTITY_VERSION,  # always use this constant
                        entity=response_data,  # the validated data object
                        workflow=process_brands  # Workflow function applied asynchronously before persistence.
                    )
                    job["status"] = "completed"
                    job["completedAt"] = datetime.datetime.utcnow().isoformat()
                    # Return the id from the external service.
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
@app.route('/api/brands/update', methods=['POST'])
@validate_request(UpdateRequest)
async def update_brands(data: UpdateRequest):
    """
    Initiates fetching data from the external API,
    delegating any additional async tasks or entity transformations 
    to the workflow function before persistence.
    """
    job_id = str(uuid.uuid4())
    job = {
        "id": job_id,
        "status": "processing",
        "requestedAt": datetime.datetime.utcnow().isoformat()
    }
    JOBS[job_id] = job

    # Process the job and await the result.
    result = await asyncio.create_task(process_entity(job, data.__dict__))

    if result is not None:
        return jsonify({
            "status": "success",
            "data": result,  # Return the external id.
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

# GET endpoint to retrieve brand data.
@app.route('/api/brands', methods=['GET'])
async def get_brands():
    """
    Retrieves the current stored brand data from the external service.
    """
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