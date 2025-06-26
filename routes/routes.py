 from dataclasses import dataclass
import asyncio
import logging
import uuid
from datetime import datetime
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
class PetSearchRequest:
    type: str = None
    status: str = None
    tags: list[str] = None

@dataclass
class AdoptPetRequest:
    petId: str  # changed to string id
    adopterName: str

class AsyncCache:
    def __init__(self):
        self._adoptions = {}
        self._lock = asyncio.Lock()

    async def add_adoption(self, adopter_name: str, pet: dict):
        async with self._lock:
            if adopter_name not in self._adoptions:
                self._adoptions[adopter_name] = []
            self._adoptions[adopter_name].append(pet)

    async def get_adoptions(self, adopter_name: str):
        async with self._lock:
            return self._adoptions.get(adopter_name, [])

cache = AsyncCache()
PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

async def query_pets(type_: str = None, status: str = None, tags: list[str] = None) -> list[dict]:
    params = {}
    if status:
        params["status"] = status
    url = f"{PETSTORE_API_BASE}/pet/findByStatus"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(f"Failed to fetch pets from external API: {e}")
            return []
    def pet_matches(pet: dict) -> bool:
        if type_ and pet.get("category", {}).get("name", "").lower() != type_.lower():
            return False
        if tags:
            pet_tags = [t.get("name", "").lower() for t in pet.get("tags", [])]
            if not all(t.lower() in pet_tags for t in tags):
                return False
        return True
    return [p for p in pets if pet_matches(p)]

# Workflow function for petsearchrequest entity
async def process_petsearchrequest(entity: dict) -> dict:
    pets = await query_pets(entity.get("type"), entity.get("status"), entity.get("tags"))
    entity["pets"] = pets
    return entity

# Workflow function for adoptpetrequest entity
async def process_adoptpetrequest(entity: dict) -> dict:
    pet_id = entity.get("petId")
    adopter_name = entity.get("adopterName")
    pet_info = None

    try:
        all_searches = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="petsearchrequest",
            entity_version=ENTITY_VERSION,
        )
        for search in all_searches:
            pets = search.get("pets")
            if pets is None:
                pets = await query_pets(search.get("type"), search.get("status"), search.get("tags"))
            for pet in pets:
                if str(pet.get("id")) == str(pet_id):
                    pet_info = {
                        "id": str(pet.get("id")),
                        "name": pet.get("name"),
                        "type": pet.get("category", {}).get("name"),
                        "status": pet.get("status")
                    }
                    break
            if pet_info:
                break
    except Exception as e:
        logger.exception("Failed to find pet info from petsearchrequest entities: %s", e)

    if pet_info is None:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{PETSTORE_API_BASE}/pet/{pet_id}")
                resp.raise_for_status()
                pet = resp.json()
                pet_info = {
                    "id": str(pet.get("id")),
                    "name": pet.get("name"),
                    "type": pet.get("category", {}).get("name"),
                    "status": pet.get("status")
                }
        except Exception as e:
            logger.warning("Failed to fetch pet info from external API: %s", e)
            pet_info = {"id": str(pet_id), "name": None, "type": None, "status": None}

    await cache.add_adoption(adopter_name, pet_info)

    entity["adoptionStatus"] = "confirmed"
    entity["petInfo"] = pet_info

    return entity

@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearchRequest)
async def pets_search(data: PetSearchRequest):
    data_dict = {
        "type": data.type,
        "status": data.status,
        "tags": data.tags,
    }
    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="petsearchrequest",
            entity_version=ENTITY_VERSION,
            entity=data_dict
        )
        return jsonify({"searchId": id})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add pet search request"}), 500

@app.route("/pets/search/<search_id>", methods=["GET"])
async def get_search_results(search_id):
    try:
        result = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="petsearchrequest",
            entity_version=ENTITY_VERSION,
            technical_id=search_id
        )
        if not result:
            return jsonify({"error": "Search ID not found or results not ready"}), 404
        pets = result.get("pets")
        if pets is None:
            pets = await query_pets(result.get("type"), result.get("status"), result.get("tags"))
        simplified = []
        for p in pets:
            simplified.append({
                "id": str(p.get("id")),
                "name": p.get("name"),
                "type": p.get("category", {}).get("name"),
                "status": p.get("status"),
                "tags": [t.get("name") for t in p.get("tags", []) if t.get("name")]
            })
        return jsonify({"searchId": search_id, "pets": simplified})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve search results"}), 500

@app.route("/pets/adopt", methods=["POST"])
@validate_request(AdoptPetRequest)
async def adopt_pet(data: AdoptPetRequest):
    data_dict = {
        "petId": data.petId,
        "adopterName": data.adopterName,
    }
    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="adoptpetrequest",
            entity_version=ENTITY_VERSION,
            entity=data_dict
        )
        return jsonify({
            "adoptionId": id,
            "petId": data.petId,
            "adopterName": data.adopterName,
            "adoptionStatus": "confirmed"
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to process adoption request"}), 500

@app.route("/pets/adoptions/<adopter_name>", methods=["GET"])
async def get_adoptions(adopter_name):
    adopted_pets = await cache.get_adoptions(adopter_name)
    return jsonify({
        "adopterName": adopter_name,
        "adoptedPets": adopted_pets
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)