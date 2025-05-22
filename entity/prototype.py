import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request
import httpx
import random

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data models for request validation
@dataclass
class PetSearch:
    type: Optional[str] = None
    status: Optional[str] = None

@dataclass
class PetRecommendationRequest:
    type: Optional[str] = None

@dataclass
class NameGeneratorRequest:
    type: Optional[str] = None
    mood: Optional[str] = None

# Local in-memory cache for pets data keyed by petId
pets_cache: Dict[int, Dict[str, Any]] = {}

# Simulated entity job tracking (job_id -> status info)
entity_job: Dict[str, Dict[str, Any]] = {}

# Petstore API base URL
PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

@app.route("/pets/search", methods=["POST"])
# Workaround: validate_request must go after route decorator for POST requests
@validate_request(PetSearch)
async def search_pets(data: PetSearch):
    pet_type = data.type
    status = data.status

    try:
        async with httpx.AsyncClient() as client:
            query_status = status if status else "available"
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": query_status})
            resp.raise_for_status()
            pets = resp.json()

            if pet_type:
                filtered = []
                for pet in pets:
                    cat = pet.get("category")
                    cat_name = cat.get("name") if cat else None
                    if cat_name and cat_name.lower() == pet_type.lower():
                        filtered.append(pet)
                pets = filtered

            for pet in pets:
                pet_id = pet.get("id")
                if pet_id:
                    pets_cache[pet_id] = pet

            result = []
            for pet in pets:
                pet_id = pet.get("id")
                cat = pet.get("category")
                cat_name = cat.get("name") if cat else None
                result.append({
                    "id": pet_id,
                    "name": pet.get("name"),
                    "type": cat_name,
                    "status": pet.get("status"),
                })

            return jsonify({"pets": result})

    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to fetch pets from Petstore API"}), 500

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet(pet_id: int):
    pet = pets_cache.get(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found in cache. Please search first."}), 404

    cat = pet.get("category")
    cat_name = cat.get("name") if cat else None

    tags = pet.get("tags")
    if tags and isinstance(tags, list) and len(tags) > 0:
        description = ", ".join(tag.get("name") for tag in tags if tag.get("name"))
    else:
        description = "No description available."

    return jsonify({
        "id": pet.get("id"),
        "name": pet.get("name"),
        "type": cat_name,
        "status": pet.get("status"),
        "description": description,
    })

@app.route("/pets/recommendation", methods=["POST"])
# Workaround: validate_request must go after route decorator for POST requests
@validate_request(PetRecommendationRequest)
async def pet_recommendation(data: PetRecommendationRequest):
    pet_type = data.type
    pets_list = list(pets_cache.values())

    if not pets_list:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": "available"})
                resp.raise_for_status()
                pets = resp.json()
                for pet in pets:
                    pet_id = pet.get("id")
                    if pet_id:
                        pets_cache[pet_id] = pet
                pets_list = list(pets_cache.values())
        except Exception as e:
            logger.exception(e)
            return jsonify({"error": "Failed to fetch pets for recommendation"}), 500

    if pet_type:
        filtered = []
        for pet in pets_list:
            cat = pet.get("category")
            cat_name = cat.get("name") if cat else None
            if cat_name and cat_name.lower() == pet_type.lower():
                filtered.append(pet)
        pets_list = filtered

    if not pets_list:
        return jsonify({"error": "No pets found matching the criteria"}), 404

    pet = random.choice(pets_list)
    cat = pet.get("category")
    cat_name = cat.get("name") if cat else None

    fun_facts = [
        "Loves chasing laser pointers!",
        "Enjoys long naps in the sun.",
        "Always ready for a belly rub.",
        "Has a secret stash of toys.",
        "Can hear a treat bag from miles away!",
    ]
    fun_fact = random.choice(fun_facts)

    return jsonify({
        "pet": {
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": cat_name,
            "status": pet.get("status"),
            "funFact": fun_fact,
        }
    })

@app.route("/pets/name-generator", methods=["POST"])
# Workaround: validate_request must go after route decorator for POST requests
@validate_request(NameGeneratorRequest)
async def name_generator(data: NameGeneratorRequest):
    pet_type = data.type.lower() if data.type else None
    mood = data.mood.lower() if data.mood else None

    type_names = {
        "dog": ["Buddy", "Buster", "Rex", "Max", "Bouncy Buddy"],
        "cat": ["Whiskers", "Shadow", "Luna", "Mittens", "Purrfect"],
        "bird": ["Tweety", "Sky", "Sunny", "Peep", "Chirpy"],
    }

    mood_modifiers = {
        "playful": ["Bouncy", "Wiggly", "Jumpy", "Happy"],
        "calm": ["Chill", "Silent", "Mellow", "Gentle"],
        "grumpy": ["Grumpy", "Cranky", "Snappy", "Moody"],
    }

    base_names = type_names.get(pet_type, ["Fluffy", "Snowball", "Spark", "Shadow", "Lucky"])
    modifiers = mood_modifiers.get(mood, ["Happy", "Sunny", "Bright", "Clever"])

    if random.random() < 0.6:
        name = f"{random.choice(modifiers)} {random.choice(base_names)}"
    else:
        name = random.choice(base_names)

    return jsonify({"name": name})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)