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

# Request models
@dataclass
class PetFilter:
    status: Optional[str] = None

@dataclass
class PetsSyncRequest:
    filter: PetFilter

@dataclass
class PetsSearchRequest:
    name: Optional[str] = None
    status: Optional[str] = None  # comma-separated statuses
    category: Optional[str] = None

@dataclass
class AdopterInfo:
    name: str
    email: str

@dataclass
class PetsAdoptRequest:
    petId: int
    adopter: AdopterInfo

# Adoption entity for storing adoption info persistently
ADOPTION_ENTITY_NAME = "adoption"
PET_ENTITY_NAME = "pet"
PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

def transform_petstore_pet(pet: Dict) -> Dict:
    # Minimal transformation: keep only what's needed, exclude id because entity_service manages it
    return {
        "name": pet.get("name", ""),
        "category": pet.get("category") or {},
        "status": pet.get("status", "available"),
        "tags": [t.get("name") for t in pet.get("tags", []) if "name" in t],
    }

# Workflow function for 'pet' entity
async def process_pet(entity: Dict) -> Dict:
    """
    Workflow function applied to pet entity asynchronously before persistence.
    Moves enrichment and additional logic here.
    """
    category_name = entity.get("category", {}).get("name", "").lower()
    tags = entity.get("tags", [])
    # Avoid duplicate tags
    if category_name == "cat" and "purrfect" not in tags:
        tags.append("purrfect")
    elif category_name == "dog" and "woof-tastic" not in tags:
        tags.append("woof-tastic")
    elif category_name and "pet-tastic" not in tags:
        tags.append("pet-tastic")
    entity["tags"] = tags

    # Add a processed timestamp
    entity['processed_at'] = datetime.utcnow().isoformat() + 'Z'

    return entity

# Workflow function for 'adoption' entity
async def process_adoption(entity: Dict) -> Dict:
    """
    Workflow function applied to adoption entity asynchronously before persistence.
    Ensures adoption timestamp and validity.
    """
    entity['adopted_at'] = datetime.utcnow().isoformat() + 'Z'
    # Additional validations or enrichment can be added here
    return entity

@app.route("/pets/sync", methods=["POST"])
@validate_request(PetsSyncRequest)
async def pets_sync(data: PetsSyncRequest):
    filter_status = data.filter.status
    params = {}
    if filter_status:
        params["status"] = filter_status

    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params=params)
            r.raise_for_status()
            pets_raw = r.json()
        except Exception as e:
            logger.exception(e)
            return jsonify({"error": "Failed to fetch pets from external API"}), 502

    pets_transformed = [transform_petstore_pet(p) for p in pets_raw]
    count = 0
    for pet in pets_transformed:
        pet_data = pet.copy()
        # entity_service.add_item assigns id so exclude id here
        try:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model=PET_ENTITY_NAME,
                entity_version=ENTITY_VERSION,
                entity=pet_data,
                workflow=process_pet  # workflow handles enrichment, async tasks
            )
            count += 1
        except Exception as e:
            logger.exception(e)
            continue

    return jsonify({"syncedCount": count, "message": "Pets data synced successfully."})

@app.route("/pets/search", methods=["POST"])
@validate_request(PetsSearchRequest)
async def pets_search(data: PetsSearchRequest):
    name = data.name
    status_list = data.status.split(",") if data.status else None
    category = data.category

    conditions = {"cyoda": {"type": "group", "operator": "AND", "conditions": []}}
    if status_list:
        conditions["cyoda"]["conditions"].append({
            "jsonPath": "$.status",
            "operatorType": "INOT_EQUAL" if len(status_list) == 0 else "EQUALS",
            "value": status_list if len(status_list) > 1 else status_list[0],
            "type": "simple"
        })
    if name:
        conditions["cyoda"]["conditions"].append({
            "jsonPath": "$.name",
            "operatorType": "ICONTAINS",
            "value": name,
            "type": "simple"
        })
    if category:
        conditions["cyoda"]["conditions"].append({
            "jsonPath": "$.category.name",
            "operatorType": "IEQUALS",
            "value": category,
            "type": "simple"
        })

    try:
        if conditions["cyoda"]["conditions"]:
            results = await entity_service.get_items_by_condition(
                token=cyoda_auth_service,
                entity_model=PET_ENTITY_NAME,
                entity_version=ENTITY_VERSION,
                condition=conditions
            )
        else:
            results = await entity_service.get_items(
                token=cyoda_auth_service,
                entity_model=PET_ENTITY_NAME,
                entity_version=ENTITY_VERSION,
            )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to search pets"}), 500

    for r in results:
        if "id" in r:
            r["id"] = str(r["id"])

    return jsonify({"results": results})

@app.route("/pets/<string:pet_id>", methods=["GET"])
async def pets_get(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Pet not found"}), 404

    if not pet:
        return jsonify({"error": "Pet not found"}), 404

    if "id" in pet:
        pet["id"] = str(pet["id"])

    return jsonify(pet)

@app.route("/pets/adopt", methods=["POST"])
@validate_request(PetsAdoptRequest)
async def pets_adopt(data: PetsAdoptRequest):
    pet_id = str(data.petId)
    adopter = data.adopter
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Pet not found"}), 404

    if not pet:
        return jsonify({"error": "Pet not found"}), 404

    if pet.get("status") != "available":
        return jsonify({"success": False, "message": f"Sorry, {pet.get('name')} is not available for adoption."}), 400

    pet["status"] = "adopted"
    try:
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=pet,
            technical_id=pet_id,
            meta={}
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"success": False, "message": "Failed to update pet status."}), 500

    # Create adoption entity to persist adoption info
    adoption_data = {
        "petId": pet_id,
        "adopterName": adopter.name,
        "adopterEmail": adopter.email,
        "petName": pet.get("name"),
    }
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=ADOPTION_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=adoption_data,
            workflow=process_adoption
        )
    except Exception as e:
        logger.exception(e)
        # Adoption info persistence failure is non-critical for user experience
        pass

    return jsonify({"success": True, "message": f"Congrats {adopter.name}! You adopted {pet.get('name')}."})

@app.route("/adoptions/<string:adopter_email>", methods=["GET"])
async def get_adoptions(adopter_email: str):
    # Query adoption entities filtered by adopterEmail
    conditions = {
        "cyoda": {
            "type": "group",
            "operator": "AND",
            "conditions": [{
                "jsonPath": "$.adopterEmail",
                "operatorType": "IEQUALS",
                "value": adopter_email,
                "type": "simple"
            }]
        }
    }
    try:
        adoptions = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model=ADOPTION_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            condition=conditions
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to fetch adoptions"}), 500

    pets = []
    for adoption in adoptions:
        pet_id = adoption.get("petId")
        if not pet_id:
            continue
        try:
            pet = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model=PET_ENTITY_NAME,
                entity_version=ENTITY_VERSION,
                technical_id=pet_id
            )
            if pet:
                pet["id"] = str(pet["id"])
                pets.append({"id": pet["id"], "name": pet.get("name"), "category": pet.get("category", {})})
        except Exception:
            continue

    return jsonify({"adopter": adopter_email, "adoptedPets": pets})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)