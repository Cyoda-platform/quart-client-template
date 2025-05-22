import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

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

# In-memory async-safe cache
class AsyncCache:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._pets: Dict[int, Dict] = {}
        self._adoptions: Dict[str, List[int]] = {}

    async def set_pets(self, pets: List[Dict]):
        async with self._lock:
            for pet in pets:
                self._pets[pet["id"]] = pet

    async def get_pet(self, pet_id: int) -> Optional[Dict]:
        async with self._lock:
            return self._pets.get(pet_id)

    async def search_pets(self, name: Optional[str], status: Optional[List[str]], category: Optional[str]) -> List[Dict]:
        async with self._lock:
            results = list(self._pets.values())
        if name:
            results = [p for p in results if name.lower() in p.get("name", "").lower()]
        if status:
            results = [p for p in results if p.get("status") in status]
        if category:
            results = [p for p in results if p.get("category", {}).get("name", "").lower() == category.lower()]
        return results

    async def add_adoption(self, adopter_email: str, pet_id: int):
        async with self._lock:
            self._adoptions.setdefault(adopter_email, [])
            if pet_id not in self._adoptions[adopter_email]:
                self._adoptions[adopter_email].append(pet_id)

    async def get_adoptions(self, adopter_email: str) -> List[int]:
        async with self._lock:
            return self._adoptions.get(adopter_email, [])

cache = AsyncCache()
PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

def transform_petstore_pet(pet: Dict) -> Dict:
    pet_id = pet.get("id")
    name = pet.get("name", "")
    category = pet.get("category") or {}
    status = pet.get("status", "available")
    tags = [t.get("name") for t in pet.get("tags", []) if "name" in t]
    if category.get("name", "").lower() == "cat":
        tags.append("purrfect")
    elif category.get("name", "").lower() == "dog":
        tags.append("woof-tastic")
    else:
        tags.append("pet-tastic")
    return {"id": pet_id, "name": name, "category": category, "status": status, "tags": tags}

@app.route("/pets/sync", methods=["POST"])
@validate_request(PetsSyncRequest)  # workaround: validate last for POST due to quartz-schema defect
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
    await cache.set_pets(pets_transformed)
    return jsonify({"syncedCount": len(pets_transformed), "message": "Pets data synced successfully."})

@app.route("/pets/search", methods=["POST"])
@validate_request(PetsSearchRequest)  # workaround: validate last for POST due to quartz-schema defect
async def pets_search(data: PetsSearchRequest):
    name = data.name
    status_list = data.status.split(",") if data.status else None
    category = data.category
    results = await cache.search_pets(name=name, status=status_list, category=category)
    return jsonify({"results": results})

@app.route("/pets/<int:pet_id>", methods=["GET"])
# no validation needed for GET requests without query params
async def pets_get(pet_id: int):
    pet = await cache.get_pet(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404
    return jsonify(pet)

@app.route("/pets/adopt", methods=["POST"])
@validate_request(PetsAdoptRequest)  # workaround: validate last for POST due to quartz-schema defect
async def pets_adopt(data: PetsAdoptRequest):
    pet_id = data.petId
    adopter = data.adopter
    pet = await cache.get_pet(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404
    if pet.get("status") != "available":
        return jsonify({"success": False, "message": f"Sorry, {pet['name']} is not available for adoption."}), 400
    pet["status"] = "adopted"
    await cache.set_pets([pet])
    await cache.add_adoption(adopter.email, pet_id)
    return jsonify({"success": True, "message": f"Congrats {adopter.name}! You adopted {pet['name']}."})

@app.route("/adoptions/<string:adopter_email>", methods=["GET"])
# no validation needed for GET requests without query params
async def get_adoptions(adopter_email: str):
    pet_ids = await cache.get_adoptions(adopter_email)
    pets = []
    for pid in pet_ids:
        pet = await cache.get_pet(pid)
        if pet:
            pets.append({"id": pet["id"], "name": pet["name"], "category": pet.get("category", {})})
    return jsonify({"adopter": adopter_email, "adoptedPets": pets})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)