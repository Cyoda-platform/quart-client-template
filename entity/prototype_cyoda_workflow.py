import asyncio
import aiohttp
import logging
from dataclasses import dataclass
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request
from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Quart(__name__)
QuartSchema(app)

@app.before_serving
async def startup():
    # Initialize the connection to the cyoda service
    await init_cyoda(cyoda_token)

@dataclass
class FetchBrandsRequest:
    fetch_mode: str = None  # Optional parameter for future use

# This function logs additional activity about the processed entity.
async def log_entity_activity(entity):
    try:
        # Prepare supplementary data for logging.
        log_data = {
            "brand_id": entity.get("id"),
            "status": "processed",
            "message": "Entity processed and stored successfully."
        }
        # Persist the log as a supplementary entity of a different model.
        await entity_service.add_item(
            token=cyoda_token,
            entity_model="activity_logs",
            entity_version=ENTITY_VERSION,
            entity=log_data,
            workflow=None  # No workflow applied for logging.
        )
        logger.info("Activity log created for brand id: %s", entity.get("id"))
    except Exception as ex:
        # Log the error without affecting the main workflow.
        logger.error("Failed to log entity activity: %s", ex)

# Workflow function to process the 'brands' entity before persistence.
async def process_brands(entity):
    try:
        # Modify the entity state before persistence.
        entity["processed"] = True

        # Also, add additional meta data if missing.
        if "metadata" not in entity:
            entity["metadata"] = {}
        entity["metadata"]["processed_timestamp"] = asyncio.get_event_loop().time()

        # Perform additional asynchronous operations (fire and forget).
        asyncio.create_task(log_entity_activity(entity))
    except Exception as ex:
        # Log any error that occurs during processing; do not stop persistence.
        logger.error("Error in process_brands workflow: %s", ex)
    return entity

@app.route('/fetch-brands', methods=['POST'])
@validate_request(FetchBrandsRequest)  # Validation decorator must be placed after the route decorator.
async def fetch_brands(data: FetchBrandsRequest):
    try:
        # Fetch data from the external API.
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.practicesoftwaretesting.com/brands",
                headers={"accept": "application/json"}
            ) as resp:
                if resp.status != 200:
                    logger.error("External API responded with status %s", resp.status)
                    return jsonify({"error": "Failed to fetch external data."}), 500
                external_data = await resp.json()
    except Exception as e:
        logger.exception("Exception during external API call")
        return jsonify({"error": str(e)}), 500

    try:
        # Persist the fetched data with the workflow function applied.
        item_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,  # Always use this constant
            entity=external_data,           # Validated external data
            workflow=process_brands         # Apply the workflow asynchronously before persistence.
        )
    except Exception as e:
        logger.exception("Exception during persisting entity")
        return jsonify({"error": "Failed to store entity data."}), 500

    return jsonify({
        "id": item_id,
        "message": "Data fetched and stored successfully."
    })

@app.route('/brands', methods=['GET'])
async def get_brands():
    try:
        # Retrieve processed brand data from the external entity service.
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model="brands",
            entity_version=ENTITY_VERSION,
        )
        return jsonify(data)
    except Exception as e:
        logger.exception("Exception fetching brand data")
        return jsonify({"error": "Failed to retrieve brand data."}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)