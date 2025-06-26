from dataclasses import dataclass
import asyncio
import logging
import uuid
from datetime import datetime
import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class PetSearchRequest:
    type: str = None
    status: str = None
    tags: list[str] = None

@dataclass
class AdoptPetRequest:
    petId: int
    adopterName: str

class AsyncCache:
    def __init__(self):
        self._search_results = {}
        self._adoptions = {}
        self._lock = asyncio.Lock()

    async def save_search(self, search_id: str, pets: list[dict]):
        async with self._lock:
            self._search_results[search_id] = pets

    async def get_search(self, search_id: str):
        async with self._lock:
            return self._search_results.get(search_id)

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

@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearchRequest)  # workaround issue: validation last for POST
async def pets_search(data: PetSearchRequest):
    search_id = str(uuid.uuid4())
    logger.info(f"Received pet search request {search_id} with filters type={data.type}, status={data.status}, tags={data.tags}")
    async def process_search(search_id, type_, status, tags):
        pets = await query_pets(type_, status, tags)
        simplified = []
        for p in pets:
            simplified.append({
                "id": p.get("id"),
                "name": p.get("name"),
                "type": p.get("category", {}).get("name"),
                "status": p.get("status"),
                "tags": [t.get("name") for t in p.get("tags", []) if t.get("name")]
            })
        await cache.save_search(search_id, simplified)
        logger.info(f"Processed pet search {search_id} with {len(simplified)} results")
    asyncio.create_task(process_search(search_id, data.type, data.status, data.tags))
    return jsonify({"searchId": search_id})

@app.route("/pets/search/<search_id>", methods=["GET"])
async def get_search_results(search_id):
    pets = await cache.get_search(search_id)
    if pets is None:
        return jsonify({"error": "Search ID not found or results not ready"}), 404
    return jsonify({"searchId": search_id, "pets": pets})

@app.route("/pets/adopt", methods=["POST"])
@validate_request(AdoptPetRequest)  # workaround issue: validation last for POST
async def adopt_pet(data: AdoptPetRequest):
    pet_id = data.petId
    adopter_name = data.adopterName
    pet_info = None
    for sid in list(cache._search_results.keys()):
        pets = await cache.get_search(sid)
        if pets:
            for pet in pets:
                if pet["id"] == pet_id:
                    pet_info = pet
                    break
        if pet_info:
            break
    if pet_info is None:
        pet_info = {"id": pet_id, "name": None, "type": None, "status": None}
    await cache.add_adoption(adopter_name, pet_info)
    logger.info(f"Pet {pet_id} adopted by {adopter_name}")
    return jsonify({
        "petId": pet_id,
        "adopterName": adopter_name,
        "adoptionStatus": "confirmed"
    })

@app.route("/pets/adoptions/<adopter_name>", methods=["GET"])
async def get_adoptions(adopter_name):
    adopted_pets = await cache.get_adoptions(adopter_name)
    return jsonify({
        "adopterName": adopter_name,
        "adoptedPets": adopted_pets
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)