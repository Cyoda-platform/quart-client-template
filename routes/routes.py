from dataclasses import dataclass
import asyncio
import logging
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
class PetSearchQuery:
    type: Optional[str] = None
    status: Optional[str] = None
    name: Optional[str] = None

@dataclass
class NewPet:
    name: str
    type: str
    status: str
    photoUrls: Optional[List[str]] = None

@dataclass
class PetStatusUpdate:
    status: str

PET_ENTITY_NAME = "pet"
PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"

async def process_pet(entity: Dict) -> Dict:
    # Normalize status to lowercase if present
    if 'status' in entity and isinstance(entity['status'], str):
        entity['status'] = entity['status'].lower()

    # Add processed timestamp in ISO-8601 UTC format
    entity['processed_at'] = datetime.utcnow().isoformat() + 'Z'

    # Enrich pet entity with supplementary data from petstore API
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            params = {}
            if entity.get('status'):
                params['status'] = entity['status']
            response = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params=params)
            response.raise_for_status()
            pets = response.json()

            filtered = []
            name_lower = entity.get('name', '').lower()
            type_lower = entity.get('type', '').lower()
            for pet in pets:
                pet_type = pet.get('category', {}).get('name', '').lower()
                pet_name = pet.get('name', '').lower()
                if pet_type == type_lower and name_lower in pet_name:
                    filtered.append(pet)

            entity['petstore_matches_count'] = len(filtered)
            entity['petstore_sample_matches'] = filtered[:3]

    except Exception as e:
        logger.warning(f"Failed to enrich pet entity with petstore data: {e}")

    return entity

@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearchQuery)
async def search_pets(data: PetSearchQuery):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            pets = []
            if data.status:
                r = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": data.status})
                r.raise_for_status()
                pets = r.json()
            else:
                pets_accum = []
                for st in ["available", "pending", "sold"]:
                    r = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": st})
                    if r.status_code == 200:
                        pets_accum.extend(r.json())
                pets = pets_accum

            def pet_matches(pet):
                if data.type:
                    pet_type = pet.get("category", {}).get("name", "")
                    if pet_type.lower() != data.type.lower():
                        return False
                if data.name:
                    pet_name = pet.get("name", "")
                    if data.name.lower() not in pet_name.lower():
                        return False
                return True

            pets = [p for p in pets if pet_matches(p)]

            result = [{
                "id": str(p.get("id")),
                "name": p.get("name"),
                "type": p.get("category", {}).get("name", ""),
                "status": p.get("status", ""),
                "photoUrls": p.get("photoUrls", []),
            } for p in pets]

            return jsonify({"pets": result})

    except Exception as e:
        logger.exception(f"Error fetching pets from Petstore API: {e}")
        return jsonify({"error": "Failed to fetch pets"}), 500

@app.route("/pets", methods=["POST"])
@validate_request(NewPet)
async def add_pet(data: NewPet):
    pet_data = {
        "name": data.name,
        "type": data.type,
        "status": data.status,
        "photoUrls": data.photoUrls or [],
    }
    try:
        pet_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=pet_data
        )
        logger.info(f"Pet added with ID {pet_id} and name {data.name}")
        return jsonify({"id": str(pet_id), "message": "Pet added successfully"}), 201
    except Exception as e:
        logger.exception(f"Failed to add pet: {e}")
        return jsonify({"error": "Failed to add pet"}), 500

@app.route("/pets", methods=["GET"])
async def get_all_pets():
    try:
        pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        return jsonify({"pets": pets})
    except Exception as e:
        logger.exception(f"Failed to retrieve pets: {e}")
        return jsonify({"error": "Failed to retrieve pets"}), 500

@app.route("/pets/<pet_id>", methods=["GET"])
async def get_pet_by_id(pet_id):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
        )
        if not pet:
            return jsonify({"error": "Pet not found"}), 404
        return jsonify(pet)
    except Exception as e:
        logger.exception(f"Failed to retrieve pet by id {pet_id}: {e}")
        return jsonify({"error": "Failed to retrieve pet"}), 500

@app.route("/pets/<pet_id>/status", methods=["POST"])
@validate_request(PetStatusUpdate)
async def update_pet_status(data: PetStatusUpdate, pet_id):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
        )
        if not pet:
            return jsonify({"error": "Pet not found"}), 404

        pet["status"] = data.status

        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=pet,
            technical_id=pet_id,
            meta={}
        )

        logger.info(f"Updated pet {pet_id} status to {data.status}")
        return jsonify({"id": pet_id, "message": "Status updated successfully"})
    except Exception as e:
        logger.exception(f"Failed to update pet status for {pet_id}: {e}")
        return jsonify({"error": "Failed to update pet status"}), 500

if __name__ == '__main__':
    import sys
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
