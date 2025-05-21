import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache to mock persistence
class Cache:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._pets: List[Dict] = []
        self._last_updated: Optional[datetime] = None

    async def update_pets(self, pets: List[Dict]):
        async with self._lock:
            self._pets = pets
            self._last_updated = datetime.utcnow()

    async def get_pets(self) -> List[Dict]:
        async with self._lock:
            return self._pets.copy()

cache = Cache()

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

FUN_FACTS = {
    "cat": ["Cats sleep for 70% of their lives.", "A group of cats is called a clowder.", "Cats have five toes on their front paws, but only four on the back."],
    "dog": ["Dogs have three eyelids.", "Dogs can learn more than 1000 words.", "A dog's sense of smell is 40 times better than humans."],
    "all": ["Pets can reduce stress and anxiety.", "Owning a pet can improve heart health.", "Many pets have unique ways of showing affection."]
}

async def fetch_pets_from_petstore(pet_type: Optional[str], status: Optional[str]) -> List[Dict]:
    params = {"status": status or "available"}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params=params, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(e)
            return []
    if pet_type and pet_type.lower() != "all":
        pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == pet_type.lower()]
    mapped = []
    for pet in pets:
        mapped.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name"),
            "status": pet.get("status"),
            "photoUrls": pet.get("photoUrls", []),
        })
    return mapped

@dataclass
class PetFetch:
    type: Optional[str]
    status: Optional[str]

@dataclass
class FunFact:
    type: Optional[str]

@dataclass
class PetMatch:
    preferredType: Optional[str]
    preferredStatus: Optional[str]

@app.route("/pets/fetch", methods=["POST"])
@validate_request(PetFetch)  # validation last for POST (workaround for quart-schema issue)
async def pets_fetch(data: PetFetch):
    pets = await fetch_pets_from_petstore(data.type, data.status)
    await cache.update_pets(pets)
    return jsonify({"success": True, "pets": pets, "message": "Data fetched from Petstore API"})

@app.route("/pets/fun-fact", methods=["POST"])
@validate_request(FunFact)  # validation last for POST (workaround for quart-schema issue)
async def pets_fun_fact(data: FunFact):
    import random
    pet_type = (data.type or "all").lower()
    facts_pool = FUN_FACTS.get(pet_type, FUN_FACTS["all"])
    fun_fact = random.choice(facts_pool) if facts_pool else "Pets are awesome!"
    return jsonify({"success": True, "funFact": fun_fact})

@validate_querystring(PetFetch)  # validation first for GET (workaround for quart-schema issue)
@app.route("/pets", methods=["GET"])
async def pets_get():
    pets = await cache.get_pets()
    return jsonify({"success": True, "pets": pets})

@app.route("/pets/match", methods=["POST"])
@validate_request(PetMatch)  # validation last for POST (workaround for quart-schema issue)
async def pets_match(data: PetMatch):
    preferred_type = (data.preferredType or "").lower()
    preferred_status = (data.preferredStatus or "").lower()
    pets = await cache.get_pets()
    filtered = pets
    if preferred_type:
        filtered = [p for p in filtered if (p.get("type") or "").lower() == preferred_type]
    if preferred_status:
        filtered = [p for p in filtered if (p.get("status") or "").lower() == preferred_status]
    if filtered:
        import random
        recommended_pet = random.choice(filtered)
        return jsonify({"success": True, "recommendedPet": recommended_pet})
    return jsonify({"success": False, "message": "No pet matches your preferences. Try fetching pets first or change filters."})

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)