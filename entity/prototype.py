from dataclasses import dataclass
import asyncio
import logging
import random
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# workaround: due to quart-schema defect, PUT/POST validation must go last, GET validation goes first

# request models
@dataclass
class SearchPets:
    type: str = None
    status: str = None
    name: str = None

@dataclass
class RandomPet:
    type: str = None

@dataclass
class FunFact:
    type: str = None

# In-memory cache for pets keyed by pet id
pets_cache = {}

# Fun facts for pets
FUN_FACTS = {
    "cat": [
        "Cats sleep 70% of their lives.",
        "A group of cats is called a clowder.",
        "Cats have five toes on their front paws, but only four toes on their back paws."
    ],
    "dog": [
        "Dogs have three eyelids.",
        "Dogs’ sense of smell is about 40 times better than humans'.",
        "Dogs can learn more than 1000 words."
    ],
    "default": [
        "Pets bring joy and companionship to humans.",
        "Playing with pets can reduce stress and anxiety."
    ]
}

PETSTORE_BASE = "https://petstore.swagger.io/v2"
async_client = httpx.AsyncClient(timeout=10)

async def fetch_pets_from_petstore(params: dict):
    status = params.get("status", "available")
    try:
        r = await async_client.get(f"{PETSTORE_BASE}/pet/findByStatus", params={"status": status})
        r.raise_for_status()
        pets = r.json()
        filtered = []
        type_filter = (params.get("type") or "").lower()
        name_filter = (params.get("name") or "").lower()
        for pet in pets:
            pet_type = pet.get("category", {}).get("name", "").lower() if pet.get("category") else ""
            pet_name = (pet.get("name") or "").lower()
            if type_filter and pet_type != type_filter:
                continue
            if name_filter and name_filter not in pet_name:
                continue
            item = {
                "id": pet["id"],
                "name": pet.get("name", ""),
                "type": pet_type,
                "status": pet.get("status", ""),
                "photoUrls": pet.get("photoUrls", [])
            }
            filtered.append(item)
            pets_cache[pet["id"]] = item
        return filtered
    except Exception as e:
        logger.exception(e)
        return []

async def fetch_pet_by_id_from_cache(pet_id: int):
    return pets_cache.get(pet_id)

async def fetch_random_pet(type_filter: str = None):
    params = {"status": "available"}
    if type_filter:
        params["type"] = type_filter
    pets = await fetch_pets_from_petstore(params)
    if pets:
        return random.choice(pets)
    return None

def get_fun_fact(pet_type: str = None):
    pet_type = (pet_type or "").lower()
    facts = FUN_FACTS.get(pet_type) or FUN_FACTS["default"]
    return random.choice(facts)

@app.route("/pets/search", methods=["POST"])
@validate_request(SearchPets)
async def pets_search(data: SearchPets):
    pets = await fetch_pets_from_petstore(data.__dict__)
    return jsonify({"pets": pets})

@app.route("/pets/random", methods=["POST"])
@validate_request(RandomPet)
async def pets_random(data: RandomPet):
    pet = await fetch_random_pet(data.type)
    if pet:
        return jsonify({"pet": pet})
    return jsonify({"pet": None}), 404

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def pets_get(pet_id):
    pet = await fetch_pet_by_id_from_cache(pet_id)
    if pet:
        return jsonify(pet)
    return jsonify({"message": "Pet not found in cache. Please search first."}), 404

@app.route("/pets/funfact", methods=["POST"])
@validate_request(FunFact)
async def pets_funfact(data: FunFact):
    fact = get_fun_fact(data.type)
    return jsonify({"fact": fact})

@app.before_serving
async def startup():
    logger.info("Starting up async http client")

@app.after_serving
async def shutdown():
    await async_client.aclose()
    logger.info("Closed async http client")

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)