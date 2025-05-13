from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from uuid import uuid4

import httpx
from quart import Quart, jsonify
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
class PetSearch:
    type: str
    status: str
    name: str = None

@dataclass
class AdoptRequest:
    petId: str
    adopterName: str
    contactInfo: str

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

async def fetch_pets_from_petstore(type_, status, name):
    params = {}
    if type_ and type_.lower() != "all":
        params["type"] = type_.lower()
    if status and status.lower() != "all":
        params["status"] = status.lower()
    status_param = params.get("status", "available")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": status_param})
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(e)
            return []
    filtered = []
    for pet in pets:
        pet_type = pet.get("category", {}).get("name", "").lower() if pet.get("category") else ""
        pet_name = pet.get("name", "").lower()
        if type_.lower() != "all" and pet_type != type_.lower():
            continue
        if name and name.lower() not in pet_name:
            continue
        filtered.append({
            "id": str(pet.get("id")),
            "name": pet.get("name", ""),
            "type": pet_type or "unknown",
            "status": pet.get("status", ""),
            "description": pet.get("tags")[0]["name"] if pet.get("tags") else "",
            "imageUrl": pet.get("photoUrls")[0] if pet.get("photoUrls") else "",
        })
    return filtered

async def process_pet(entity_data):
    # No modification needed currently; placeholder for enrichment or validation
    return entity_data

async def process_adoption_request(entity_data):
    entity_data["status"] = "pending"
    entity_data["requestedAt"] = datetime.utcnow().isoformat()

    adoption_id = entity_data.get("adoptionId")
    pet_id = entity_data.get("petId")

    # Validate pet existence
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=str(pet_id)
        )
        if not pet:
            entity_data["status"] = "failed"
            entity_data["failureReason"] = "Pet not found"
            logger.warning(f"Adoption request failed: pet {pet_id} not found")
            return entity_data
    except Exception as e:
        logger.exception(e)
        entity_data["status"] = "failed"
        entity_data["failureReason"] = "Pet lookup error"
        return entity_data

    async def approve_adoption():
        try:
            await asyncio.sleep(2)
            entity_data["status"] = "approved"
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="adoption_request",
                entity_version=ENTITY_VERSION,
                entity=entity_data,
                technical_id=adoption_id,
                meta={}
            )
            logger.info(f"Adoption {adoption_id} approved for pet {pet_id}")
        except Exception as e:
            logger.exception(e)
            entity_data["status"] = "error"
            try:
                await entity_service.update_item(
                    token=cyoda_auth_service,
                    entity_model="adoption_request",
                    entity_version=ENTITY_VERSION,
                    entity=entity_data,
                    technical_id=adoption_id,
                    meta={}
                )
            except Exception as e2:
                logger.exception(e2)

    asyncio.create_task(approve_adoption())

    return entity_data

@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearch)
async def pets_search(data: PetSearch):
    pets = await fetch_pets_from_petstore(data.type, data.status, data.name)
    for pet in pets:
        try:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                entity=pet
            )
        except Exception as e:
            logger.exception(e)
    return jsonify({"pets": pets})

@app.route("/pets/adopt", methods=["POST"])
@validate_request(AdoptRequest)
async def pets_adopt(data: AdoptRequest):
    adoption_id = str(uuid4())
    adoption_record = {
        "adoptionId": adoption_id,
        "petId": data.petId,
        "adopterName": data.adopterName,
        "contactInfo": data.contactInfo,
    }
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="adoption_request",
            entity_version=ENTITY_VERSION,
            entity=adoption_record
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Failed to submit adoption request"}), 500

    return jsonify({"message": "Adoption request submitted successfully", "adoptionId": adoption_id})

@app.route("/pets/<pet_id>", methods=["GET"])
async def get_pet(pet_id):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=str(pet_id)
        )
    except Exception as e:
        logger.exception(e)
        pet = None
    if not pet:
        return jsonify({"message": "Pet not found"}), 404
    return jsonify(pet)

@app.route("/adoptions/<adoption_id>", methods=["GET"])
async def get_adoption(adoption_id):
    try:
        adoption = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="adoption_request",
            entity_version=ENTITY_VERSION,
            technical_id=str(adoption_id)
        )
    except Exception as e:
        logger.exception(e)
        adoption = None
    if not adoption:
        return jsonify({"message": "Adoption request not found"}), 404
    return jsonify(adoption)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)