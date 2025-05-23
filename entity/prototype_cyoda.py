from dataclasses import dataclass
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data classes for request validation
@dataclass
class PetSearchQuery:
    type: str = None
    status: str = None
    name: str = None

@dataclass
class NewPet:
    name: str
    type: str
    status: str
    photoUrls: List[str] = None

@dataclass
class PetStatusUpdate:
    status: str

PET_ENTITY_NAME = "pet"

PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"

async def fetch_pets_from_petstore(type_: Optional[str], status: Optional[str], name: Optional[str]) -> List[Dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        pets = []
        try:
            if status:
                r = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": status})
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
                if type_:
                    pet_type = pet.get("category", {}).get("name", "")
                    if pet_type.lower() != type_.lower():
                        return False
                if name:
                    pet_name = pet.get("name", "")
                    if name.lower() not in pet_name.lower():
                        return False
                return True
            pets = [p for p in pets if pet_matches(p)]
            return pets
        except Exception as e:
            logger.exception(f"Error fetching pets from Petstore API: {e}")
            return []

@app.route("/pets/search", methods=["POST"])
# workaround: validate_request should be last for POST due to quart-schema defect
@validate_request(PetSearchQuery)
async def search_pets(data: PetSearchQuery):
    pets = await fetch_pets_from_petstore(data.type, data.status, data.name)
    def map_pet(pet):
        return {
            "id": str(pet.get("id")),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name", ""),
            "status": pet.get("status", ""),
            "photoUrls": pet.get("photoUrls", []),
        }
    mapped_pets = [map_pet(p) for p in pets]
    return jsonify({"pets": mapped_pets})

@app.route("/pets", methods=["POST"])
# workaround: validate_request should be last for POST due to quart-schema defect
@validate_request(NewPet)
async def add_pet(data: NewPet):
    if not (data.name and data.type and data.status):
        return jsonify({"error": "Missing required fields: name, type, status"}), 400
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
        logger.info(f"Pet added to entity_service: {pet_id} - {data.name}")
        return jsonify({"id": str(pet_id), "message": "Pet added successfully"}), 201
    except Exception as e:
        logger.exception(e)
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
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pets"}), 500

@app.route("/pets/<pet_id>", methods=["GET"])
async def get_pet_by_id(pet_id):
    # pet_id now always string
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
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pet"}), 500

@app.route("/pets/<pet_id>/status", methods=["POST"])
# workaround: validate_request should be last for POST due to quart-schema defect
@validate_request(PetStatusUpdate)
async def update_pet_status(data: PetStatusUpdate, pet_id):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
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
        logger.exception(e)
        return jsonify({"error": "Failed to update pet status"}), 500

if __name__ == '__main__':
    import sys
    import logging
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)