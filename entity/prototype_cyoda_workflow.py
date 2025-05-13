import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class Pet_search_request:
    type: Optional[str]
    status: Optional[str]
    name: Optional[str]

@dataclass
class Add_pet_request:
    name: str
    type: str
    status: str
    photoUrls: Optional[str] = None  # comma-separated placeholder

@dataclass
class Update_pet_request:
    name: Optional[str]
    type: Optional[str]
    status: Optional[str]
    photoUrls: Optional[str] = None

external_pets_cache: Dict[str, List[Dict]] = {}

PETSTORE_API_BASE = "https://petstore3.swagger.io/api/v3"

def make_cache_key(filters: Dict) -> str:
    return "|".join(f"{k}={v}" for k, v in sorted(filters.items()) if v) or "all"

@app.route("/pets/search", methods=["POST"])
@validate_request(Pet_search_request)
async def search_pets(data: Pet_search_request):
    filters = {
        "type": data.type,
        "status": data.status,
        "name": data.name,
    }
    cache_key = make_cache_key(filters)
    if cache_key in external_pets_cache:
        logger.info(f"Returning cached external pets for key: {cache_key}")
        return jsonify({"pets": external_pets_cache[cache_key]})

    pets = await fetch_external_pets(filters)
    simplified = [simplify_pet(p) for p in pets]
    external_pets_cache[cache_key] = simplified
    return jsonify({"pets": simplified})

async def fetch_external_pets(filters: Dict) -> List[Dict]:
    async with httpx.AsyncClient() as client:
        try:
            status = filters.get("status") or "available"
            r = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": status})
            r.raise_for_status()
            pets = r.json()
            if filters.get("type"):
                pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == filters["type"].lower()]
            if filters.get("name"):
                pets = [p for p in pets if filters["name"].lower() in p.get("name", "").lower()]
            return pets
        except Exception:
            logger.exception("Failed to fetch external pets")
            return []

def simplify_pet(p: Dict) -> Dict:
    return {
        "id": p.get("id"),
        "name": p.get("name"),
        "type": p.get("category", {}).get("name"),
        "status": p.get("status"),
        "photoUrls": p.get("photoUrls", []),
    }

@app.route("/pets/<string:pet_id>", methods=["GET"])
async def get_pet(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
        if pet is None:
            for pets_list in external_pets_cache.values():
                for p in pets_list:
                    if str(p.get("id")) == pet_id:
                        return jsonify(p)
            return jsonify({"error": "Pet not found"}), 404
        return jsonify(pet)
    except Exception:
        logger.exception("Failed to retrieve pet")
        return jsonify({"error": "Failed to retrieve pet"}), 500

async def process_pet(entity: dict) -> dict:
    entity['processed_at'] = datetime.utcnow().isoformat() + "Z"

    if 'type' in entity and isinstance(entity['type'], str):
        entity['type'] = entity['type'].lower()
    if 'status' in entity and isinstance(entity['status'], str):
        entity['status'] = entity['status'].lower()

    if 'photoUrls' in entity:
        if isinstance(entity['photoUrls'], str):
            entity['photoUrls'] = [url.strip() for url in entity['photoUrls'].split(",") if url.strip()]
        elif not isinstance(entity['photoUrls'], list):
            entity['photoUrls'] = []

    # Example of async fire-and-forget task (uncomment and implement if needed)
    # asyncio.create_task(some_async_notification(entity))

    return entity

@app.route("/pets", methods=["POST"])
@validate_request(Add_pet_request)
async def add_pet(data: Add_pet_request):
    pet_data = {
        "name": data.name,
        "type": data.type,
        "status": data.status,
        "photoUrls": data.photoUrls or "",
    }
    try:
        pet_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=pet_data,
            workflow=process_pet,
        )
        logger.info(f"Added pet with id {pet_id}: {data.name}")
        return jsonify({"id": pet_id, "message": "Pet added successfully"}), 201
    except Exception:
        logger.exception("Failed to add pet")
        return jsonify({"error": "Failed to add pet"}), 500

@app.route("/pets/<string:pet_id>/update", methods=["POST"])
@validate_request(Update_pet_request)
async def update_pet(data: Update_pet_request, pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
        if pet is None:
            return jsonify({"error": "Pet not found"}), 404

        if data.name is not None:
            pet["name"] = data.name
        if data.type is not None:
            pet["type"] = data.type
        if data.status is not None:
            pet["status"] = data.status
        if data.photoUrls is not None:
            pet["photoUrls"] = data.photoUrls

        # We can optionally apply the workflow on update here if desired,
        # but since workflow is designed for add_item, keep update simple.

        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=pet,
            technical_id=pet_id,
            meta={}
        )
        logger.info(f"Updated pet {pet_id}")
        return jsonify({"message": "Pet updated successfully"})
    except Exception:
        logger.exception("Failed to update pet")
        return jsonify({"error": "Failed to update pet"}), 500

@app.route("/pets/<string:pet_id>/delete", methods=["POST"])
async def delete_pet(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
        if pet is None:
            return jsonify({"error": "Pet not found"}), 404

        await entity_service.delete_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
            meta={}
        )
        logger.info(f"Deleted pet {pet_id}")
        return jsonify({"message": "Pet deleted successfully"})
    except Exception:
        logger.exception("Failed to delete pet")
        return jsonify({"error": "Failed to delete pet"}), 500

if __name__ == '__main__':
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)