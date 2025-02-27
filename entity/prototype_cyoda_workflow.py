#!/usr/bin/env python3
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
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

# Dataclass for POST /fetch-brands request
@dataclass
class FetchBrandsRequest:
    fetchType: str  # Expected to be "all" or other modes as required

@app.route('/fetch-brands', methods=['POST'])
@validate_request(FetchBrandsRequest)
async def fetch_brands(data: FetchBrandsRequest):
    """
    POST /fetch-brands
    Triggers the external API call and fires a background task to process the data.
    """
    # Generate a placeholder job id; in production, use UUID or a similar unique identifier
    job_id = "job_placeholder"

    # Create a simple entity job dict to simulate job processing information.
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
    Process the external API call, fetch brands data, and store each brand via the external entity_service.
    This function runs asynchronously in the background.
    """
    external_api_url = 'https://api.practicesoftwaretesting.com/brands'
    headers = {'accept': 'application/json'}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(external_api_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    # Iterate over each brand item and call the external service to add the item.
                    for item in data:
                        # Instead of embedding asynchronous tasks here (fire and forget),
                        # we delegate any additional async processing to the workflow function.
                        await entity_service.add_item(
                            token=cyoda_token,
                            entity_model="brands",
                            entity_version=ENTITY_VERSION,  # always use this constant
                            entity=item,  # the validated data object
                            workflow=process_brands  # Workflow function applied to the entity before persistence
                        )
                    entity_job[job_id]["status"] = "completed"
                else:
                    entity_job[job_id]["status"] = "failed"
    except Exception as e:
        entity_job[job_id]["status"] = "failed"
        # Log the exception as needed
        print(f"Error processing entity job {job_id}: {e}")

async def process_brands(entity):
    # Workflow function applied to the brand entity before persistence.
    # Modify entity state directly and perform any async tasks to enrich the data.
    entity["processedAt"] = datetime.datetime.utcnow().isoformat()
    # For example, fetch supplementary info asynchronously and add to the entity.
    supplementary_info = await fetch_supplementary_info(entity)
    entity["supplementaryInfo"] = supplementary_info
    return entity

async def fetch_supplementary_info(entity):
    # This asynchronous function simulates fetching extra data based on the brand's details.
    # This is a placeholder for any asynchronous tasks (e.g., external API call).
    await asyncio.sleep(0.1)  # Simulate async I/O delay
    # Example: generate supplementary info based on the entity's "name" field.
    name = entity.get("name", "unknown")
    return {"info": f"Additional details based on {name}"}

@app.route('/brands', methods=['GET'])
async def get_brands():
    """
    GET /brands
    Retrieves the list of brands stored via the external entity_service.
    """
    # Retrieve all brand items via the external service.
    items = await entity_service.get_items(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,
    )
    if items:
        return jsonify(items)
    else:
        return jsonify({"message": "No brands found."})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)