```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from quart import Quart, jsonify, request
from quart_schema import QuartSchema
import httpx
import random

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Local in-memory cache for pets data keyed by petId
pets_cache: Dict[int, Dict[str, Any]] = {}

# Simulated entity job tracking (job_id -> status info)
entity_job: Dict[str, Dict[str, Any]] = {}

# Petstore API base URL
PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"


@app.route("/pets/search", methods=["POST"])
async def search_pets():
    """
    POST /pets/search
    Request JSON:
      {
        "type": "dog",           # optional
        "status": "available"    # optional
      }
    Response JSON:
      {
        "pets": [ {pet}, ... ]
      }
    """
    data = await request.get_json(force=True)
    pet_type = data.get("type")
    status = data.get("status")

    # Petstore API: GET /pet/findByStatus?status=available
    # Petstore API does not support type filtering on server side, so filter client-side.

    try:
        async with httpx.AsyncClient() as client:
            # If status not provided, use "available" to reduce data size (can be adjusted)
            query_status = status if status else "available"
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": query_status})
            resp.raise_for_status()
            pets = resp.json()

            # Filter by type if provided (type corresponds to 'category.name' in petstore)
            if pet_type:
                filtered_pets = []
                for pet in pets:
                    cat = pet.get("category")
                    cat_name = cat.get("name") if cat else None
                    if cat_name and cat_name.lower() == pet_type.lower():
                        filtered_pets.append(pet)
                pets = filtered_pets

            # Cache pets by id for later GET /pets/{petId}
            for pet in pets:
                pet_id = pet.get("id")
                if pet_id:
                    pets_cache[pet_id] = pet

            # Respond with simplified pet info (id, name, type, status)
            result = []
            for pet in pets:
                pet_id = pet.get("id")
                cat = pet.get("category")
                cat_name = cat.get("name") if cat else None
                result.append(
                    {
                        "id": pet_id,
                        "name": pet.get("name"),
                        "type": cat_name,
                        "status": pet.get("status"),
                    }
                )

            return jsonify({"pets": result})

    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to fetch pets from Petstore API"}), 500


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet(pet_id: int):
    """
    GET /pets/{petId}
    Response JSON:
      {
        id, name, type, status, description (if available)
      }
    """
    pet = pets_cache.get(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found in cache. Please search first."}), 404

    cat = pet.get("category")
    cat_name = cat.get("name") if cat else None

    # Compose description from tags or placeholders
    tags = pet.get("tags")
    description = None
    if tags and isinstance(tags, list) and len(tags) > 0:
        description = ", ".join(tag.get("name") for tag in tags if tag.get("name"))
    else:
        description = "No description available."

    return jsonify(
        {
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": cat_name,
            "status": pet.get("status"),
            "description": description,
        }
    )


@app.route("/pets/recommendation", methods=["POST"])
async def pet_recommendation():
    """
    POST /pets/recommendation
    Request JSON:
      {
        "type": "cat"  # optional
      }
    Response JSON:
      {
        "pet": {id, name, type, status, funFact}
      }
    """
    data = await request.get_json(force=True)
    pet_type = data.get("type")

    # Use cached pets for recommendation; if empty, fetch default available pets first
    pets_list = list(pets_cache.values())

    if not pets_list:
        # No cached pets - fetch some default available pets to seed cache
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

    # Filter by type if given
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

    # Fun facts placeholder - TODO: Could be extended with real facts DB or API
    fun_facts = [
        "Loves chasing laser pointers!",
        "Enjoys long naps in the sun.",
        "Always ready for a belly rub.",
        "Has a secret stash of toys.",
        "Can hear a treat bag from miles away!",
    ]
    fun_fact = random.choice(fun_facts)

    return jsonify(
        {
            "pet": {
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": cat_name,
                "status": pet.get("status"),
                "funFact": fun_fact,
            }
        }
    )


@app.route("/pets/name-generator", methods=["POST"])
async def name_generator():
    """
    POST /pets/name-generator
    Request JSON:
      {
        "type": "dog",      # optional
        "mood": "playful"   # optional
      }
    Response JSON:
      {
        "name": "Bouncy Buddy"
      }
    """
    data = await request.get_json(force=True)
    pet_type = data.get("type", "").lower() if data.get("type") else None
    mood = data.get("mood", "").lower() if data.get("mood") else None

    # Simple name generation logic based on type and mood
    # TODO: Replace with more advanced logic or external service

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

    # Randomly combine modifier + base name or just base name
    if random.random() < 0.6:
        name = f"{random.choice(modifiers)} {random.choice(base_names)}"
    else:
        name = random.choice(base_names)

    return jsonify({"name": name})


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
