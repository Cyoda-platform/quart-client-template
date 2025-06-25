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

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

@dataclass
class FetchPetsRequest:
    type: Optional[str] = None
    status: Optional[str] = None

@dataclass
class AdoptPetRequest:
    petId: int

PETSTORE_BASE = "https://petstore3.swagger.io/api/v3"

async def fetch_pets_from_petstore(
    type_filter: Optional[str] = None, status_filter: Optional[str] = None
) -> List[dict]:
    status = status_filter or "available"
    url = f"{PETSTORE_BASE}/pet/findByStatus"
    params = {"status": status}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(f"Failed fetching pets from Petstore API: {e}")
            return []
    if type_filter:
        pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == type_filter.lower()]
    return pets

async def update_pet_adoption_status_in_petstore(pet_id: int) -> bool:
    get_url = f"{PETSTORE_BASE}/pet/{pet_id}"
    update_url = f"{PETSTORE_BASE}/pet"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(get_url, timeout=10)
            resp.raise_for_status()
            pet = resp.json()
            if not pet:
                logger.info(f"Pet ID {pet_id} not found in Petstore.")
                return False
            pet["status"] = "adopted"
            resp_update = await client.put(update_url, json=pet, timeout=10)
            resp_update.raise_for_status()
            return True
        except Exception as e:
            logger.exception(f"Failed to update adoption status in Petstore for pet {pet_id}: {e}")
            return False

async def process_fetch_pets(data: dict):
    pets = await fetch_pets_from_petstore(
        type_filter=data.get("type"),
        status_filter=data.get("status"),
    )
    for pet in pets:
        # add each pet to entity_service
        try:
            # convert id to string as technical_id is string
            pet_id = pet.get("id")
            if not pet_id:
                continue
            # remove id from pet data because id will be managed by entity_service
            pet_data = pet.copy()
            pet_data.pop("id", None)
            # Add pet item, discard returned id because it's new id assigned by entity_service
            _ = await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                entity=pet_data
            )
        except Exception as e:
            logger.exception(f"Failed to add pet to entity_service: {e}")

async def process_adopt_pet(pet_id: int) -> bool:
    success = await update_pet_adoption_status_in_petstore(pet_id)
    if success:
        try:
            # Update entity_service item with new status
            # pet_id must be string now
            id_str = str(pet_id)
            pet = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                technical_id=id_str
            )
            if pet:
                pet["status"] = "adopted"
                await entity_service.update_item(
                    token=cyoda_auth_service,
                    entity_model="pet",
                    entity_version=ENTITY_VERSION,
                    entity=pet,
                    technical_id=id_str,
                    meta={}
                )
        except Exception as e:
            logger.exception(f"Failed to update pet adoption status in entity_service: {e}")
    return success

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)
async def fetch_pets(data: FetchPetsRequest):
    asyncio.create_task(process_fetch_pets(data.__dict__))
    return jsonify({"message": "Pet data fetch started. Please GET /pets to see cached results."}), 202

@app.route("/pets/adopt", methods=["POST"])
@validate_request(AdoptPetRequest)
async def adopt_pet(data: AdoptPetRequest):
    pet_id_str = str(data.petId)
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id_str
        )
    except Exception as e:
        logger.exception(f"Error retrieving pet from entity_service: {e}")
        return jsonify({"error": "Internal server error."}), 500

    if not pet:
        return jsonify({"error": f"Pet with ID {pet_id_str} not found. Please fetch pets first."}), 404

    success = await process_adopt_pet(data.petId)
    if not success:
        return jsonify({"error": "Failed to adopt pet via external API."}), 500
    return jsonify({"message": f"Pet with ID {pet_id_str} has been adopted."})

@app.route("/pets", methods=["GET"])
async def get_pets():
    try:
        pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
        )
        # pets is expected to be a list of dicts with technical_id included
        pets_list = []
        for pet in pets:
            pet_copy = pet.copy()
            # status is included in pet data from entity_service
            pets_list.append(pet_copy)
        return jsonify({"pets": pets_list})
    except Exception as e:
        logger.exception(f"Failed to get pets from entity_service: {e}")
        return jsonify({"error": "Failed to retrieve pets."}), 500

@app.route("/pets/<string:pet_id>", methods=["GET"])
async def get_pet(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
        if not pet:
            return jsonify({"error": f"Pet with ID {pet_id} not found."}), 404
        return jsonify(pet)
    except Exception as e:
        logger.exception(f"Failed to get pet from entity_service: {e}")
        return jsonify({"error": "Failed to retrieve pet."}), 500

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        level=logging.INFO,
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)