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

@dataclass
class QueryFilters:
    status: Optional[str]
    category: Optional[str]
    tags: Optional[List[str]]

@dataclass
class PetIdRequest:
    id: str  # string technical_id

ENTITY_PET = "pet"
ENTITY_PET_QUERY = "pet_query"
ENTITY_PET_DETAIL = "pet_detail"

async def process_pet(entity_data: Dict[str, Any]) -> None:
    # Add processed timestamp
    entity_data['processed_at'] = datetime.utcnow().isoformat()
    # Set default status if missing
    if 'status' not in entity_data or entity_data['status'] is None:
        entity_data['status'] = 'new'
    # Example enrichment or validation can go here, safely async
    # Avoid any add/update/delete on ENTITY_PET inside this workflow

async def process_pet_query(entity_data: Dict[str, Any]) -> None:
    filters = {}
    if 'status' in entity_data and entity_data['status'] is not None:
        filters['status'] = entity_data['status']
    if 'category' in entity_data and entity_data['category'] is not None:
        filters['category'] = entity_data['category']
    if 'tags' in entity_data and entity_data['tags'] is not None:
        filters['tags'] = entity_data['tags']

    try:
        await process_pets_query(filters)
        entity_data['result_status'] = 'completed'
    except Exception as e:
        logger.error(f"Error processing pet_query workflow: {e}")
        entity_data['result_status'] = 'failed'
        entity_data['error_message'] = str(e)
    finally:
        entity_data['processed_at'] = datetime.utcnow().isoformat()

async def process_pet_detail_workflow(entity_data: Dict[str, Any]) -> None:
    pet_id = entity_data.get('id')
    if not pet_id:
        logger.warning("pet_detail entity missing 'id' field.")
        entity_data['result_status'] = 'failed'
        entity_data['error_message'] = "'id' field is required"
        entity_data['processed_at'] = datetime.utcnow().isoformat()
        return
    try:
        await process_pet_detail(pet_id)
        entity_data['result_status'] = 'completed'
    except Exception as e:
        logger.error(f"Error processing pet_detail workflow for id {pet_id}: {e}")
        entity_data['result_status'] = 'failed'
        entity_data['error_message'] = str(e)
    finally:
        entity_data['processed_at'] = datetime.utcnow().isoformat()

async def process_pets_query(filters: Dict[str, Any]) -> None:
    logger.info(f"Processing pets query with filters: {filters}")
    await asyncio.sleep(1)  # Simulate async processing
    logger.info("Finished processing pets query.")

async def process_pet_detail(pet_id: str) -> None:
    logger.info(f"Processing pet detail for id: {pet_id}")
    await asyncio.sleep(1)  # Simulate async processing
    logger.info(f"Finished processing pet detail for id: {pet_id}")

@app.route("/pets/query", methods=["POST"])
@validate_request(QueryFilters)
async def pets_query(data: QueryFilters):
    query_entity = {
        "status": data.status,
        "category": data.category,
        "tags": data.tags,
        "requested_at": datetime.utcnow().isoformat(),
    }
    try:
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_PET_QUERY,
            entity_version=ENTITY_VERSION,
            entity=query_entity,
            workflow=process_pet_query,
        )
    except Exception as e:
        logger.error(f"Failed to add pet_query entity: {e}")
        return jsonify({"error": "Failed to process pets query"}), 500
    return jsonify({
        "status": "processing",
        "entityId": entity_id,
        "requestedAt": query_entity["requested_at"]
    }), 202

@app.route("/pets", methods=["GET"])
async def get_pets():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_PET,
            entity_version=ENTITY_VERSION,
        )
        if not items:
            return jsonify({"error": "No pets data found."}), 404
        return jsonify(items)
    except Exception as e:
        logger.error(f"Failed to retrieve pets data: {e}")
        return jsonify({"error": "Failed to retrieve pets data."}), 500

@app.route("/pets/details", methods=["POST"])
@validate_request(PetIdRequest)
async def pet_details_post(data: PetIdRequest):
    detail_entity = {
        "id": data.id,
        "requested_at": datetime.utcnow().isoformat(),
    }
    try:
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_PET_DETAIL,
            entity_version=ENTITY_VERSION,
            entity=detail_entity,
            workflow=process_pet_detail_workflow,
        )
    except Exception as e:
        logger.error(f"Failed to add pet_detail entity: {e}")
        return jsonify({"error": "Failed to process pet detail request"}), 500
    return jsonify({
        "status": "processing",
        "entityId": entity_id,
        "requestedAt": detail_entity["requested_at"],
        "petId": data.id
    }), 202

@app.route("/pets/details/<pet_id>", methods=["GET"])
async def pet_details_get(pet_id: str):
    try:
        pet_detail = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_PET,
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
        )
        if pet_detail is None:
            return jsonify({
                "error": f"No details found for pet ID {pet_id}. Please POST /pets/details first."
            }), 404
        return jsonify(pet_detail)
    except Exception as e:
        logger.error(f"Failed to retrieve pet details for id {pet_id}: {e}")
        return jsonify({"error": f"Failed to retrieve details for pet ID {pet_id}."}), 500

async def add_new_pet(data: Dict[str, Any]) -> str:
    try:
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_PET,
            entity_version=ENTITY_VERSION,
            entity=data,
            workflow=process_pet
        )
        return entity_id
    except Exception as e:
        logger.error(f"Failed to add new pet entity: {e}")
        raise

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)