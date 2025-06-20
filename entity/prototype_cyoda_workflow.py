from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

import httpx
from quart import Quart, jsonify, request, abort
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

async def process_pet(entity: Dict[str, Any]) -> Dict[str, Any]:
    # Add last processed timestamp
    entity['last_processed'] = datetime.utcnow().isoformat() + 'Z'

    # Add or update description
    name = entity.get("name") or "Unknown"
    pet_type = entity.get("type") or "pet"
    entity['description'] = f"{name} is a lovely {pet_type}."

    # Add adopted flag asynchronously
    pet_id = entity.get("id")
    adopted = False
    if pet_id is not None:
        adopted = await app_state.is_adopted(str(pet_id))
    entity['adopted'] = adopted

    return entity

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

    for pet in all_pets:
        pet_id = pet.get("id")
        if pet_id is None:
            continue

        entity_pet = {
            "id": str(pet_id),
            "type": pet.get("category", {}).get("name") if pet.get("category") else None,
            "name": pet.get("name"),
            "status": pet.get("status"),
            "photoUrls": pet.get("photoUrls", []),
        }

        try:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                entity=entity_pet,
                workflow=process_pet
            )
            logger.info(f"Added/Updated pet with id {pet_id} in entity service")
        except Exception as e:
            logger.exception(f"Error syncing pet id={pet_id} to entity_service: {e}")

    return jsonify({"results": all_pets})

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