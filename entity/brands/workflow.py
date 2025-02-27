from datetime import datetime
import asyncio
import aiohttp
import uuid

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from app_init.app_init import cyoda_token, entity_service
from common.repository.cyoda.cyoda_init import init_cyoda

async def process_set_processed_timestamp(entity):
    # Set a processed timestamp on the entity.
    entity['processed_at'] = datetime.utcnow().isoformat() + "Z"

async def process_compute_summary(entity):
    # Compute a summary based on the number of brands.
    # If the entity is a list, use its length; otherwise, count as 1.
    count = len(entity) if isinstance(entity, list) else 1
    summary = {
        "brand_count": count,
        "logged_at": datetime.utcnow().isoformat() + "Z",
        "summary_id": str(uuid.uuid4())
    }
    # Instead of creating a supplementary entity via entity_service.add_item,
    # we modify the current entity state directly.
    entity['brands_summary'] = summary

async def process_fire_and_forget_task(entity):
    try:
        # Simulate additional asynchronous processing.
        await asyncio.sleep(0.1)
    except Exception as e:
        print(f"Error in fire-and-forget task: {e}")

app = Quart(__name__)
QuartSchema(app)

@app.route('/brands', methods=['POST'])
@validate_request(json=True)
async def brands_endpoint():
    entity = await request.get_json()
    await process_brands(entity)
    return jsonify(entity)