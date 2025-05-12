from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, request, jsonify
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

entity_job: Dict[str, Dict[str, Any]] = {}

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"


@dataclass
class PetFilter:
    type: Optional[str] = None
    status: Optional[str] = None
    name: Optional[str] = None


@dataclass
class PetCreate:
    name: str
    type: str
    status: str = "available"
    category: str = "pets"
    photoUrls: List[str] = field(default_factory=list)


@dataclass
class PetUpdate:
    name: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    photoUrls: Optional[List[str]] = None


async def fetch_pets_from_petstore(filters: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{PETSTORE_API_BASE}/pet/findByStatus"
    status = filters.get("status", "available")
    params = {"status": status}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets = resp.json()

            filtered = []
            pet_type = filters.get("type")
            name = filters.get("name")

            for pet in pets:
                if pet_type and pet.get("category", {}).get("name", "").lower() != pet_type.lower():
                    continue
                if name and name.lower() not in pet.get("name", "").lower():
                    continue
                filtered.append(pet)

            return {"pets": filtered}

    except Exception as e:
        logger.exception(e)
        return {"pets": []}


@app.route("/pets/search", methods=["POST"])
@validate_request(PetFilter)  # POST validation last per workaround
async def search_pets(data: PetFilter):
    filters = data.__dict__
    job_id = str(datetime.utcnow().timestamp())
    entity_job[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}

    async def process_search():
        result = await fetch_pets_from_petstore(filters)
        entity_job[job_id]["status"] = "done"
        entity_job[job_id]["result"] = result

    asyncio.create_task(process_search())

    await asyncio.sleep(1)
    result = entity_job[job_id].get("result", {"pets": []})
    return jsonify(result)


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet(pet_id: int):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
        if not pet:
            return jsonify({"error": "Pet not found"}), 404
        return jsonify(pet)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Error retrieving pet"}), 500


@app.route("/pets", methods=["POST"])
@validate_request(PetCreate)  # POST validation last per workaround
async def create_pet(data: PetCreate):
    pet_data = {
        "name": data.name,
        "type": data.type,
        "status": data.status,
        "category": data.category,
        "photoUrls": data.photoUrls,
    }
    try:
        pet_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=pet_data
        )
        return jsonify({"id": pet_id, "message": "Pet created successfully"}), 201
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Error creating pet"}), 500


@app.route("/pets/<int:pet_id>", methods=["POST"])
@validate_request(PetUpdate)  # POST validation last per workaround
async def update_pet(pet_id: int, data: PetUpdate):
    try:
        existing_pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
        if not existing_pet:
            return jsonify({"error": "Pet not found"}), 404

        updated_pet = existing_pet.copy()
        if data.name is not None:
            updated_pet["name"] = data.name
        if data.type is not None:
            updated_pet["type"] = data.type
        if data.status is not None:
            updated_pet["status"] = data.status
        if data.category is not None:
            updated_pet["category"] = data.category
        if data.photoUrls is not None:
            updated_pet["photoUrls"] = data.photoUrls

        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=updated_pet,
            technical_id=pet_id,
            meta={}
        )
        return jsonify({"id": pet_id, "message": "Pet updated successfully"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Error updating pet"}), 500


@app.route("/pets/<int:pet_id>/delete", methods=["POST"])
async def delete_pet(pet_id: int):
    try:
        existing_pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
        if not existing_pet:
            return jsonify({"error": "Pet not found"}), 404

        await entity_service.delete_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
            meta={}
        )
        return jsonify({"id": pet_id, "message": "Pet deleted successfully"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Error deleting pet"}), 500


if __name__ == '__main__':
    import sys
    import logging

    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)