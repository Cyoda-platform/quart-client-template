import asyncio
import aiohttp
from dataclasses import dataclass
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request  # Using validate_request in POST endpoint
from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

@dataclass
class FetchBrandsRequest:
    fetch_mode: str = None  # Optional parameter for future use

# Asynchronous auxiliary function to log processing activity for the entity.
async def log_entity_activity(entity):
    # Prepare supplementary data for activity log.
    log_data = {
        "brand_id": entity.get("id"),
        "message": "Entity processed and stored successfully."
    }
    # Add a supplementary entity of a different model to avoid recursion.
    await entity_service.add_item(
        token=cyoda_token,
        entity_model="activity_logs",
        entity_version=ENTITY_VERSION,
        entity=log_data,
        workflow=None  # No additional workflow for logging.
    )

# Workflow function applied to the 'brands' entity before persistence.
async def process_brands(entity):
    # Modify the current entity state.
    entity["processed"] = True
    # Perform additional asynchronous tasks (fire and forget).
    asyncio.create_task(log_entity_activity(entity))
    return entity

@app.route('/fetch-brands', methods=['POST'])
@validate_request(FetchBrandsRequest)  # Workaround for quart-schema: validation decorator goes after route decorator in POST
async def fetch_brands(data: FetchBrandsRequest):
    # Fetch data from the external API.
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                "https://api.practicesoftwaretesting.com/brands",
                headers={"accept": "application/json"}
            ) as resp:
                if resp.status != 200:
                    return jsonify({"error": "Failed to fetch external data."}), 500
                external_data = await resp.json()
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Store the fetched data in the external entity service with the workflow applied.
    item_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=external_data,  # the validated data object
        workflow=process_brands  # Workflow function applied asynchronously before persistence.
    )

    # Return only the id in the response.
    return jsonify({
        "id": item_id,
        "message": "Data fetched and stored successfully."
    })

@app.route('/brands', methods=['GET'])
async def get_brands():
    # Retrieve processed brand data from the external entity service.
    data = await entity_service.get_items(
        token=cyoda_token,
        entity_model="brands",
        entity_version=ENTITY_VERSION,
    )
    return jsonify(data)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)