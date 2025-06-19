```python
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory caches (async-safe by design as simple dicts, no globals used outside async context)
# key: searchId; value: dict with pet list and metadata
_search_results_cache: Dict[str, Dict] = {}

# key: userId; value: set of petIds
_user_favorites_cache: Dict[str, set] = {}

# Fun facts by pet type (simple static mapping)
FUN_FACTS = {
    "cat": "Cats are curious and love to explore!",
    "dog": "Dogs are loyal and friendly companions.",
    "bird": "Birds are social and enjoy singing.",
    "rabbit": "Rabbits have nearly 360-degree panoramic vision.",
    # Add more pet types and facts as desired
}

# External Petstore API base (Swagger Petstore, public)
PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

# HTTP client instance - reuse for all requests
http_client = httpx.AsyncClient(timeout=10.0)


async def fetch_pets_from_petstore(
    type_filter: Optional[str], status_filter: Optional[str], name_contains: Optional[str]
) -> List[Dict]:
    """
    Fetch pets from Petstore API by criteria.
    Petstore has /pet/findByStatus and /pet/findByTags endpoints.
    We'll use /pet/findByStatus with optional filtering.
    """
    pets = []

    try:
        # Petstore API requires at least one status for /pet/findByStatus, so if none provided, default to 'available'
        status_query = status_filter if status_filter else "available"

        # Petstore endpoint returns list of pets with given status
        url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
        response = await http_client.get(url, params={"status": status_query})
        response.raise_for_status()
        pet_list = response.json()

        for pet in pet_list:
            # Filter by type if provided (pet.category.name)
            pet_type = None
            if pet.get("category") and isinstance(pet["category"], dict):
                pet_type = pet["category"].get("name", "").lower()

            if type_filter and (not pet_type or pet_type != type_filter.lower()):
                continue

            # Filter by nameContains if provided
            pet_name = pet.get("name", "").lower()
            if name_contains and name_contains.lower() not in pet_name:
                continue

            # Append filtered pet
            pets.append(
                {
                    "id": pet.get("id"),
                    "name": pet.get("name"),
                    "type": pet_type or "unknown",
                    "status": status_query,
                }
            )
    except Exception as e:
        logger.exception(f"Error fetching pets from Petstore API: {e}")

    return pets


async def process_search_request(search_id: str, criteria: dict):
    """
    Process search job: fetch from external API, enrich with fun facts, store results.
    """
    try:
        pets = await fetch_pets_from_petstore(
            criteria.get("type"),
            criteria.get("status"),
            criteria.get("nameContains"),
        )

        # Add fun facts
        for pet in pets:
            fact = FUN_FACTS.get(pet["type"].lower(), "Every pet is unique and special!")
            pet["funFact"] = fact

        # Store results in cache
        _search_results_cache[search_id] = {
            "requestedAt": datetime.utcnow().isoformat() + "Z",
            "criteria": criteria,
            "pets": pets,
            "status": "completed",
        }
        logger.info(f"Search completed for searchId={search_id}, {len(pets)} pets found")
    except Exception as e:
        logger.exception(f"Failed processing search {search_id}: {e}")
        _search_results_cache[search_id] = {
            "requestedAt": datetime.utcnow().isoformat() + "Z",
            "criteria": criteria,
            "pets": [],
            "status": "failed",
        }


@app.route("/pets/search", methods=["POST"])
async def pets_search():
    """
    POST /pets/search
    Body: {"type": "...", "status": "...", "nameContains": "..."}
    Returns: {"searchId": "..."}
    """
    try:
        data = await request.get_json(force=True)
        # Basic validation on keys is omitted (dynamic data)
        search_id = str(uuid.uuid4())
        _search_results_cache[search_id] = {
            "requestedAt": datetime.utcnow().isoformat() + "Z",
            "criteria": data,
            "pets": [],
            "status": "processing",
        }

        # Fire and forget processing task
        asyncio.create_task(process_search_request(search_id, data))

        return jsonify({"searchId": search_id})
    except Exception as e:
        logger.exception(f"Error in /pets/search: {e}")
        return jsonify({"error": "Invalid request"}), 400


@app.route("/pets/results/<string:search_id>", methods=["GET"])
async def pets_results(search_id):
    """
    GET /pets/results/{searchId}
    Returns search results or status.
    """
    result = _search_results_cache.get(search_id)
    if not result:
        return jsonify({"error": "searchId not found"}), 404

    # Return pets (empty if processing or failed, but with status)
    response = {
        "searchId": search_id,
        "status": result.get("status", "unknown"),
        "pets": result.get("pets", []),
    }
    return jsonify(response)


@app.route("/pets/favorite", methods=["POST"])
async def pets_favorite():
    """
    POST /pets/favorite
    Body: {"petId": number, "userId": string}
    Adds petId to user's favorites.
    """
    try:
        data = await request.get_json(force=True)
        pet_id = data.get("petId")
        user_id = data.get("userId")

        if pet_id is None or not user_id:
            return jsonify({"error": "petId and userId required"}), 400

        # Add favorite pet for user
        favorites = _user_favorites_cache.setdefault(user_id, set())
        favorites.add(pet_id)

        return jsonify({"success": True})
    except Exception as e:
        logger.exception(f"Error in /pets/favorite: {e}")
        return jsonify({"error": "Invalid request"}), 400


@app.route("/pets/favorites/<string:user_id>", methods=["GET"])
async def pets_favorites(user_id):
    """
    GET /pets/favorites/{userId}
    Returns list of favorite pets for a user (with details if available).
    """
    favorites = _user_favorites_cache.get(user_id, set())
    pets_result = []

    # For each favorite petId, try to find pet info from search cache (simple linear search)
    # TODO: In a real app, store pet details separately for efficient lookup.
    all_pets = []
    for search_data in _search_results_cache.values():
        if search_data.get("status") != "completed":
            continue
        all_pets.extend(search_data.get("pets", []))

    pet_map = {pet["id"]: pet for pet in all_pets}

    for pet_id in favorites:
        pet = pet_map.get(pet_id)
        if pet:
            pets_result.append(
                {
                    "id": pet["id"],
                    "name": pet["name"],
                    "type": pet["type"],
                    "status": pet["status"],
                }
            )
        else:
            # Pet details not found - fallback minimal info
            pets_result.append(
                {
                    "id": pet_id,
                    "name": "Unknown",
                    "type": "Unknown",
                    "status": "Unknown",
                }
            )

    return jsonify({"userId": user_id, "favorites": pets_result})


@app.before_serving
async def startup():
    logger.info("Purrfect Pets API starting up...")


@app.after_serving
async def shutdown():
    await http_client.aclose()
    logger.info("Purrfect Pets API shutting down...")


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
