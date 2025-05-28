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

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

# Data models for request validation
@dataclass
class FetchPetsRequest:
    status: Optional[str]  # available|pending|sold
    tags: Optional[List[str]]

@dataclass
class AdoptPetRequest:
    pet_id: str  # changed to string as per instructions
    adopter_name: str
    contact: str

# Removed AsyncCache since replaced with entity_service


PET_ENTITY_NAME = "pet"
ADOPTION_ENTITY_NAME = "adoption"

PETSTORE_API_BASE = "https://petstore3.swagger.io/api/v3"

def filter_pets(pets: List[Dict], status: Optional[str], tags: Optional[List[str]]) -> List[Dict]:
    filtered = pets
    if status:
        filtered = [p for p in filtered if p.get("status") == status]
    if tags:
        filtered = [p for p in filtered if "tags" in p and any(tag in tags for tag in p["tags"])]
    return filtered

def process_petstore_pets(raw_pets: List[Dict]) -> List[Dict]:
    processed = []
    for pet in raw_pets:
        processed.append({
            "id": str(pet.get("id")) if pet.get("id") is not None else None,
            "name": pet.get("name"),
            "status": pet.get("status"),
            "category": pet.get("category", {}).get("name") if pet.get("category") else None,
            "tags": [tag.get("name") for tag in pet.get("tags", [])] if pet.get("tags") else [],
        })
    return processed

async def process_fetch_pets_job(status: Optional[str], tags: Optional[List[str]]):
    async with httpx.AsyncClient() as client:
        try:
            url = f"{PETSTORE_API_BASE}/pet/findByStatus"
            params = {"status": status or "available,pending,sold"}
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            raw_pets = response.json()
            filtered_pets = filter_pets(raw_pets, None, tags)
            processed = process_petstore_pets(filtered_pets)
            # Store each pet via entity_service
            # Clear existing pets? No instruction, so just add/update pets one by one
            for pet in processed:
                pet_id = pet.get("id")
                if pet_id:
                    try:
                        # check if pet exists
                        existing_pet = await entity_service.get_item(
                            token=cyoda_auth_service,
                            entity_model=PET_ENTITY_NAME,
                            entity_version=ENTITY_VERSION,
                            technical_id=pet_id
                        )
                        # update existing
                        await entity_service.update_item(
                            token=cyoda_auth_service,
                            entity_model=PET_ENTITY_NAME,
                            entity_version=ENTITY_VERSION,
                            entity=pet,
                            technical_id=pet_id,
                            meta={}
                        )
                    except Exception:
                        # add new pet (without id, because id is technical_id string)
                        # but entity_service expects data entity, so we add pet without id, id will be new generated
                        # But we want to keep original id as technical_id, so we must add with technical_id? 
                        # entity_service.add_item returns id, so we cannot specify id on add_item
                        # So if pet_id not exists, add new pet and ignore id field
                        pet_copy = pet.copy()
                        pet_copy.pop("id", None)
                        new_id = await entity_service.add_item(
                            token=cyoda_auth_service,
                            entity_model=PET_ENTITY_NAME,
                            entity_version=ENTITY_VERSION,
                            entity=pet_copy
                        )
                        logger.info(f"Added new pet with new id {new_id}")
                else:
                    # no id, add new pet
                    new_id = await entity_service.add_item(
                        token=cyoda_auth_service,
                        entity_model=PET_ENTITY_NAME,
                        entity_version=ENTITY_VERSION,
                        entity=pet
                    )
                    logger.info(f"Added new pet with new id {new_id}")
            logger.info(f"Fetched and processed {len(processed)} pets")
        except Exception as e:
            logger.exception(e)

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)  # validation last for POST requests (workaround for quart-schema bug)
async def fetch_pets(data: FetchPetsRequest):
    requested_at = datetime.utcnow().isoformat()
    logger.info(f"Fetch request at {requested_at} with status={data.status} tags={data.tags}")
    asyncio.create_task(process_fetch_pets_job(data.status, data.tags))
    return jsonify({"message": "Pets fetch job started"}), 202

@app.route("/pets", methods=["GET"])
async def get_pets():
    try:
        pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        return jsonify(pets)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pets"}), 500

@app.route("/pets/<string:pet_id>", methods=["GET"])
async def get_pet(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
        if pet is None:
            return jsonify({"error": "Pet not found"}), 404
        return jsonify(pet)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pet"}), 500

@app.route("/pets", methods=["POST"])
@validate_request(dict)  # generic dict for pet creation
async def add_pet(data):
    try:
        pet_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({"id": pet_id}), 201
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add pet"}), 500

@app.route("/pets/<string:pet_id>", methods=["PUT"])
@validate_request(dict)
async def update_pet(data, pet_id: str):
    try:
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=data,
            technical_id=pet_id,
            meta={}
        )
        return jsonify({"message": "Pet updated"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to update pet"}), 500

@app.route("/pets/<string:pet_id>", methods=["DELETE"])
async def delete_pet(pet_id: str):
    try:
        await entity_service.delete_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
            meta={}
        )
        return jsonify({"message": "Pet deleted"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to delete pet"}), 500

@app.route("/pets/adopt", methods=["POST"])
@validate_request(AdoptPetRequest)  # validation last for POST requests (workaround for quart-schema bug)
async def adopt_pet(data: AdoptPetRequest):
    try:
        adoption_request = {
            "request_id": str(int(datetime.utcnow().timestamp() * 1000)),
            "pet_id": data.pet_id,
            "adopter_name": data.adopter_name,
            "contact": data.contact,
            "status": "pending",
            "requested_at": datetime.utcnow().isoformat(),
        }
        adoption_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=ADOPTION_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=adoption_request
        )
        logger.info(f"New adoption request id: {adoption_id} data: {adoption_request}")
        return jsonify({"message": "Adoption request submitted", "requestId": adoption_id})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to submit adoption request"}), 500

@app.route("/adoptions", methods=["GET"])
async def get_adoptions():
    try:
        adoptions = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ADOPTION_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        return jsonify(adoptions)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve adoptions"}), 500

@app.route("/adoptions/<string:adoption_id>", methods=["GET"])
async def get_adoption(adoption_id: str):
    try:
        adoption = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=ADOPTION_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=adoption_id
        )
        if adoption is None:
            return jsonify({"error": "Adoption not found"}), 404
        return jsonify(adoption)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve adoption"}), 500

if __name__ == '__main__':
    import sys
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        level=logging.INFO,
        stream=sys.stdout,
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)