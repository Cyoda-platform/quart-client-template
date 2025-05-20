from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION
from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

# request models
@dataclass
class QueryFilters:
    status: Optional[str]
    category: Optional[str]
    tags: Optional[List[str]]

@dataclass
class PetIdRequest:
    id: str  # changed from int to str to reflect string technical_id

ENTITY_NAME = "pet"  # entity name underscore lowercase

# workaround: quart-schema defect requires validate_request after @app.route for POST
@app.route("/pets/query", methods=["POST"])
@validate_request(QueryFilters)
async def pets_query(data: QueryFilters):
    filters: Dict[str, Any] = {}
    if data.status is not None:
        filters["status"] = data.status
    if data.category is not None:
        filters["category"] = data.category
    if data.tags is not None:
        filters["tags"] = data.tags
    # No local cache usage. Use entity_service to add query as an entity or skip if not applicable
    # Here, assume we keep the existing process_pets_query logic, which might interact with external APIs or processing
    await asyncio.create_task(process_pets_query(filters))
    return jsonify({"status": "processing", "requestedAt": datetime.utcnow().isoformat()}), 202

@app.route("/pets", methods=["GET"])
async def get_pets():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        if not items:
            return jsonify({"error": "No pets data found."}), 404
        return jsonify(items)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pets data."}), 500

@app.route("/pets/details", methods=["POST"])
@validate_request(PetIdRequest)
async def pet_details_post(data: PetIdRequest):
    pet_id = data.id  # string technical id
    # process_pet_detail may still be used for external API or processing
    await asyncio.create_task(process_pet_detail(pet_id))
    return jsonify({"status": "processing", "requestedAt": datetime.utcnow().isoformat(), "petId": pet_id}), 202

@app.route("/pets/details/<pet_id>", methods=["GET"])
async def pet_details_get(pet_id: str):
    try:
        pet_detail = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
        )
        if pet_detail is None:
            return jsonify({"error": f"No details found for pet ID {pet_id}. Please POST /pets/details first."}), 404
        return jsonify(pet_detail)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": f"Failed to retrieve details for pet ID {pet_id}."}), 500

# existing helper functions and cache setup remain unchanged
# ...

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)