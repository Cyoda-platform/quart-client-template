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

@dataclass
class FetchPetsRequest:
    status: Optional[str]  # available|pending|sold
    tags: Optional[List[str]]

@dataclass
class AdoptPetRequest:
    pet_id: str
    adopter_name: str
    contact: str

PET_ENTITY_NAME = "pet"
ADOPTION_ENTITY_NAME = "adoption"
PET_FETCH_REQUEST_ENTITY_NAME = "pet_fetch_request"

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

async def process_pet(entity: Dict) -> None:
    if 'status' in entity and entity['status']:
        entity['status'] = entity['status'].lower()
    entity['processed_at'] = datetime.utcnow().isoformat()

async def process_adoption(entity: Dict) -> None:
    if 'status' not in entity or not entity['status']:
        entity['status'] = 'pending'
    entity['processed_at'] = datetime.utcnow().isoformat()

async def process_pet_fetch_request(entity: Dict) -> None:
    status = entity.get("status")
    tags = entity.get("tags")
    logger.info(f"Processing pet_fetch_request with status={status} tags={tags}")

    async with httpx.AsyncClient() as client:
        try:
            api_status = status if status else "available,pending,sold"
            url = f"{PETSTORE_API_BASE}/pet/findByStatus"
            params = {"status": api_status}
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            raw_pets = response.json()
            filtered_pets = filter_pets(raw_pets, None, tags)
            processed_pets = process_petstore_pets(filtered_pets)

            logger.info(f"Fetched {len(processed_pets)} pets from external API")

            for pet in processed_pets:
                pet_copy = pet.copy()
                pet_tech_id = pet_copy.pop("id", None)
                if pet_tech_id is not None:
                    try:
                        existing_pet = await entity_service.get_item(
                            token=cyoda_auth_service,
                            entity_model=PET_ENTITY_NAME,
                            entity_version=ENTITY_VERSION,
                            technical_id=pet_tech_id
                        )
                        await entity_service.update_item(
                            token=cyoda_auth_service,
                            entity_model=PET_ENTITY_NAME,
                            entity_version=ENTITY_VERSION,
                            entity=pet_copy,
                            technical_id=pet_tech_id,
                            meta={}
                        )
                    except Exception:
                        # If update_item with create_if_not_exists is not supported, fallback to add_item without tech id
                        try:
                            await entity_service.update_item(
                                token=cyoda_auth_service,
                                entity_model=PET_ENTITY_NAME,
                                entity_version=ENTITY_VERSION,
                                entity=pet_copy,
                                technical_id=pet_tech_id,
                                meta={},
                                create_if_not_exists=True
                            )
                        except Exception:
                            await entity_service.add_item(
                                token=cyoda_auth_service,
                                entity_model=PET_ENTITY_NAME,
                                entity_version=ENTITY_VERSION,
                                entity=pet_copy,
                                workflow=process_pet
                            )
                else:
                    await entity_service.add_item(
                        token=cyoda_auth_service,
                        entity_model=PET_ENTITY_NAME,
                        entity_version=ENTITY_VERSION,
                        entity=pet_copy,
                        workflow=process_pet
                    )
            entity['processed_at'] = datetime.utcnow().isoformat()
        except Exception as e:
            logger.exception(f"Failed to process pet_fetch_request: {e}")
            entity['error'] = str(e)

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)
async def fetch_pets(data: FetchPetsRequest):
    try:
        fetch_request = {
            "status": data.status,
            "tags": data.tags,
            "requested_at": datetime.utcnow().isoformat(),
        }
        request_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=PET_FETCH_REQUEST_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=fetch_request,
            workflow=process_pet_fetch_request
        )
        logger.info(f"Started pet fetch request {request_id} with params {fetch_request}")
        return jsonify({"message": "Pets fetch job started", "requestId": request_id}), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to start pets fetch job"}), 500

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
@validate_request(dict)
async def add_pet(data):
    try:
        pet_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=data,
            workflow=process_pet
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
@validate_request(AdoptPetRequest)
async def adopt_pet(data: AdoptPetRequest):
    try:
        adoption_request = {
            "request_id": str(int(datetime.utcnow().timestamp() * 1000)),
            "pet_id": data.pet_id,
            "adopter_name": data.adopter_name,
            "contact": data.contact,
            "requested_at": datetime.utcnow().isoformat(),
        }
        adoption_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=ADOPTION_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=adoption_request,
            workflow=process_adoption
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