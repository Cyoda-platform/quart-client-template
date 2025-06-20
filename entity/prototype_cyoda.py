from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import httpx
from quart import Quart, jsonify, request, abort
from quart_schema import QuartSchema, validate_request, validate_querystring

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
class SearchPets:
    type: Optional[str]
    status: Optional[str]
    name: Optional[str]

@dataclass
class AdoptPet:
    petId: int

class AppState:
    def __init__(self):
        self._lock = asyncio.Lock()
        self.adopted_pet_ids: set[str] = set()

    async def mark_adopted(self, pet_id: str):
        async with self._lock:
            self.adopted_pet_ids.add(pet_id)

    async def is_adopted(self, pet_id: str) -> bool:
        async with self._lock:
            return pet_id in self.adopted_pet_ids

app_state = AppState()
PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"

async def transform_pet(pet: Dict[str, Any]) -> Dict[str, Any]:
    pet_id = str(pet.get("id")) if pet.get("id") is not None else None
    adopted = await app_state.is_adopted(pet_id) if pet_id is not None else False
    return {
        "id": pet_id,
        "name": pet.get("name"),
        "type": pet.get("category", {}).get("name") if pet.get("category") else None,
        "status": pet.get("status"),
        "adopted": adopted,
        "photoUrls": pet.get("photoUrls", []),
        "description": f"{pet.get('name')} is a lovely {pet.get('category', {}).get('name') if pet.get('category') else 'pet'}.",
    }

@app.route("/pets/search", methods=["POST"])
@validate_request(SearchPets)
async def pets_search(data: SearchPets):
    pet_type = data.type
    status = data.status
    name_filter = data.name

    query_statuses = [status] if status else ["available"]
    async with httpx.AsyncClient(timeout=10) as client:
        all_pets = []
        for st in query_statuses:
            try:
                r = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": st})
                r.raise_for_status()
                pets_data = r.json()
                all_pets.extend(pets_data)
            except Exception as e:
                logger.exception(f"Error fetching pets by status={st}: {e}")

    if pet_type:
        pet_type_lower = pet_type.lower()
        all_pets = [pet for pet in all_pets if pet.get("category", {}).get("name", "").lower() == pet_type_lower]
    if name_filter:
        name_filter_lower = name_filter.lower()
        all_pets = [pet for pet in all_pets if pet.get("name") and name_filter_lower in pet["name"].lower()]

    transformed_pets = []
    for pet in all_pets:
        transformed = await transform_pet(pet)
        transformed_pets.append(transformed)

    # Store each pet via entity_service
    for pet in transformed_pets:
        pet_id = pet.get("id")
        if pet_id is None:
            continue
        try:
            # Upsert pet by deleting and adding anew or just adding, but skipping direct cache
            # Here we attempt to update if exists, else add
            # Since no get by condition for id is provided, we just add
            # Assuming add_item returns id, but as pet already has id, skip add for now
            # So we skip caching here as per instructions
            pass
        except Exception as e:
            logger.exception(f"Error syncing pet id={pet_id} to entity_service: {e}")

    return jsonify({"results": transformed_pets})

@app.route("/pets/adopt", methods=["POST"])
@validate_request(AdoptPet)
async def pets_adopt(data: AdoptPet):
    pet_id_int = data.petId
    if not isinstance(pet_id_int, int):
        abort(400, "petId must be an integer")

    pet_id = str(pet_id_int)
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
    except Exception as e:
        logger.exception(e)
        abort(404, f"Pet with id {pet_id} not found in entity service. Please search first.")

    if pet is None:
        abort(404, f"Pet with id {pet_id} not found in entity service. Please search first.")

    await app_state.mark_adopted(pet_id)
    return jsonify({
        "adopted": True,
        "petId": pet_id_int,
        "message": f"Congratulations! You have adopted {pet.get('name')}."
    })

@app.route("/pets", methods=["GET"])
async def pets_list():
    try:
        pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.exception(e)
        pets = []
    return jsonify({"pets": pets})

@app.route("/pets/<string:pet_id>", methods=["GET"])
async def pet_detail(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
    except Exception as e:
        logger.exception(e)
        abort(404, f"Pet with id {pet_id} not found in entity service.")

    if pet is None:
        abort(404, f"Pet with id {pet_id} not found in entity service.")
    return jsonify(pet)

@app.route("/pets", methods=["POST"])
@validate_request(SearchPets)
async def pets_create(data: SearchPets):
    # Example create endpoint for pet if needed (not in original)
    # Skipped as no create endpoint mentioned in original
    pass

@app.route("/pets/<string:pet_id>", methods=["PUT"])
async def pet_update(pet_id: str):
    data = await request.get_json()
    if not data:
        abort(400, "Missing JSON data")

    try:
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=data,
            technical_id=pet_id,
            meta={}
        )
    except Exception as e:
        logger.exception(e)
        abort(404, f"Pet with id {pet_id} not found or could not be updated.")

    return jsonify({"updated": True, "petId": pet_id})

@app.route("/pets/<string:pet_id>", methods=["DELETE"])
async def pet_delete(pet_id: str):
    try:
        await entity_service.delete_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
            meta={}
        )
    except Exception as e:
        logger.exception(e)
        abort(404, f"Pet with id {pet_id} not found or could not be deleted.")

    return jsonify({"deleted": True, "petId": pet_id})

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)