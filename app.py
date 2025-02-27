from common.grpc_client.grpc_client import grpc_stream
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request
from dataclasses import dataclass
import datetime
import asyncio
import aiohttp

# Import external entity_service functions and constants
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Startup routine for cyoda initialization
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

# Dataclass for POST /fetch-brands request
@dataclass
class FetchBrandsRequest:
    fetchType: str  # Expected to be "all" or other modes as required

@app.route('/fetch-brands', methods=['POST'])
@validate_request(FetchBrandsRequest)
async def fetch_brands(data: FetchBrandsRequest):
    """
    POST /fetch-brands
    Triggers the external API call and fires a background task to process and store brands data.
    """
    # Generate a placeholder job id; in production, use UUID or a similar unique identifier
    job_id = "job_placeholder"
    requested_at = datetime.datetime.utcnow()
    entity_job = {
        job_id: {
            "status": "processing",
            "requestedAt": requested_at.isoformat()
        }
    }
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(entity_job, job_id))
    return jsonify({
        "message": "Brands fetching initiated.",
        "job": entity_job[job_id]
    })

async def process_entity(entity_job, job_id):
    """
    Asynchronously fetch brands data from an external API,
    and for each brand, delegate the enrichment process to the workflow function.
    """
    external_api_url = 'https://api.practicesoftwaretesting.com/brands'
    headers = {'accept': 'application/json'}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(external_api_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    # Validate that data is a list
                    if not isinstance(data, list):
                        entity_job[job_id]["status"] = "failed"
                        print("Fetched data is not a list.")
                        return
                    for item in data:
                        if not isinstance(item, dict):
                            # Skip invalid item formats
                            continue
                        # Delegate asynchronous enrichment to the workflow function.
                        await entity_service.add_item(
                            token=cyoda_token,
                            entity_model="brands",
                            entity_version=ENTITY_VERSION,  # always use this constant
                            entity=item,  # the validated brand data
                            )
                    entity_job[job_id]["status"] = "completed"
                else:
                    entity_job[job_id]["status"] = "failed"
                    print(f"External API returned non-200 status: {response.status}")
    except Exception as e:
        entity_job[job_id]["status"] = "failed"
        print(f"Error processing entity job {job_id}: {e}")

@app.route('/brands', methods=['GET'])
async def get_brands():
    """
    GET /brands
    Retrieves the list of brands stored via the external entity_service.
    """
    try:
        items = await entity_service.get_items(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,
        )
        if items:
            return jsonify(items)
        else:
            return jsonify({"message": "No brands found."})
    except Exception as e:
        print(f"Error fetching brands: {e}")
        return jsonify({"message": "An error occurred while fetching brands."}), 500

if __name__ == '__main__':
    # Run the application; use threaded mode for compatibility.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)