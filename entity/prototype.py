from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data classes for request validation
@dataclass
class FetchPetsRequest:
    category: Optional[str]
    status: Optional[str]

@dataclass
class Preferences:
    type: Optional[str]
    ageRange: Optional[List[int]]
    friendly: Optional[bool]

@dataclass
class RecommendRequest:
    preferences: Preferences

@dataclass
class FunFactRequest:
    type: str

@dataclass
class PetQuery:
    type: Optional[str]
    status: Optional[str]

# Local async-safe cache containers
class AsyncCache:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._pets: List[Dict] = []

    async def set_pets(self, pets: List[Dict]):
        async with self._lock:
            self._pets = pets

    async def get_pets(self, type_filter: Optional[str] = None, status_filter: Optional[str] = None) -> List[Dict]:
        async with self._lock:
            result = self._pets
            if type_filter:
                result = [p for p in result if p.get("category", {}).get("name", "").lower() == type_filter.lower()]
            if status_filter:
                result = [p for p in result if p.get("status", "").lower() == status_filter.lower()]
            return result

pet_cache = AsyncCache()

async def fetch_and_cache_pets(category: Optional[str], status: Optional[str]):
    url = "https://petstore.swagger.io/v2/pet/findByStatus"
    params = {"status": status or "available"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            pets = response.json()
            if category:
                pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == category.lower()]
            await pet_cache.set_pets(pets)
            logger.info(f"Fetched and cached {len(pets)} pets")
            return len(pets)
        except Exception as e:
            logger.exception(e)
            return 0

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)  # Workaround: validate_request must be last for POST due to quart-schema bug
async def pets_fetch(data: FetchPetsRequest):
    requested_at = datetime.utcnow().isoformat()
    job_id = f"job-{requested_at}"
    asyncio.create_task(fetch_and_cache_pets(data.category, data.status))
    return jsonify({
        "message": "Data fetch started; pets will be cached asynchronously",
        "requestedAt": requested_at,
        "jobId": job_id,
    }), 202

@app.route("/pets/recommend", methods=["POST"])
@validate_request(RecommendRequest)  # Workaround: validate_request must be last for POST due to quart-schema bug
async def pets_recommend(data: RecommendRequest):
    pets = await pet_cache.get_pets()
    prefs = data.preferences
    filtered = pets
    if prefs.type:
        filtered = [p for p in filtered if p.get("category", {}).get("name", "").lower() == prefs.type.lower()]
    if prefs.ageRange and len(prefs.ageRange) == 2:
        min_age, max_age = prefs.ageRange
        def age_tag_filter(pet):
            tags = pet.get("tags") or []
            for tag in tags:
                if tag.get("name", "").startswith("age"):
                    try:
                        age = int(tag["name"][3:])
                        return min_age <= age <= max_age
                    except:
                        continue
            return True
        filtered = [p for p in filtered if age_tag_filter(p)]
    # TODO: implement friendly filter when data available
    recommendations = []
    for pet in filtered[:5]:
        recommendations.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "age": None,  # TODO: no real age info
            "type": pet.get("category", {}).get("name"),
        })
    return jsonify({"recommendations": recommendations})

@validate_querystring(PetQuery)  # Workaround: validate_querystring must be first for GET due to quart-schema bug
@app.route("/pets", methods=["GET"])
async def pets_get():
    query: PetQuery = request.args  # type: ignore
    pets = await pet_cache.get_pets(type_filter=query.type, status_filter=query.status)
    pets_out = [{
        "id": pet.get("id"),
        "name": pet.get("name"),
        "type": pet.get("category", {}).get("name"),
        "status": pet.get("status"),
    } for pet in pets]
    return jsonify({"pets": pets_out})

@app.route("/companies/<string:id>/lei", methods=["GET"])
async def get_company_lei(id):
    # No validation needed per requirements
    return jsonify({"id": id, "lei": "N/A"})

@app.route("/pets/funfact", methods=["POST"])
@validate_request(FunFactRequest)  # Workaround: validate_request must be last for POST due to quart-schema bug
async def pets_funfact(data: FunFactRequest):
    pet_type = data.type.lower()
    fun_facts = {
        "cat": "Cats have five toes on their front paws, but only four on the back.",
        "dog": "Dogs have three eyelids, including one to keep their eyes moist.",
        "bird": "Some birds can see ultraviolet light, which humans cannot.",
    }
    fact = fun_facts.get(pet_type, "Every pet is unique and full of surprises!")
    return jsonify({"funFact": fact})

if __name__ == "__main__":
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)