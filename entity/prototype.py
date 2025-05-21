from dataclasses import dataclass
from typing import List
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

# In-memory local caches
_search_results_cache = {}

_PREDEFINED_PET_FACTS = [
    "Cats sleep 70% of their lives.",
    "Dogs have three eyelids.",
    "A group of cats is called a clowder.",
    "Dogs' noses are wet to help absorb scent chemicals.",
    "Cats can rotate their ears 180 degrees.",
    "Dogs can learn more than 1000 words.",
]

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"
_async_client = httpx.AsyncClient(timeout=10.0)

@dataclass
class SearchRequest:
    type: str = None
    status: str = None
    tags: List[str] = None

@dataclass
class RandomFactRequest:
    pass

@app.route("/pets/search", methods=["POST"])
# workaround: validate_request after route for POST due to quart-schema defect
@validate_request(SearchRequest)
async def pets_search(data: SearchRequest):
    pet_type = data.type
    status = data.status
    tags = data.tags or []

    logger.info("Received search request: type=%s, status=%s, tags=%s", pet_type, status, tags)

    search_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()

    _search_results_cache[search_id] = {
        "status": "processing",
        "requestedAt": requested_at,
        "pets": [],
    }

    asyncio.create_task(_process_pet_search(search_id, pet_type, status, tags))

    return jsonify({"search_id": search_id})

async def _process_pet_search(search_id: str, pet_type: str, status: str, tags: list):
    try:
        status_query = status if status else "available"
        url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
        params = {"status": status_query}

        logger.info("Fetching pets from Petstore API with status=%s", status_query)
        r = await _async_client.get(url, params=params)
        r.raise_for_status()
        pets = r.json()

        filtered_pets = []
        for pet in pets:
            if pet_type:
                category = pet.get("category")
                if not category or category.get("name", "").lower() != pet_type.lower():
                    continue
            if tags:
                pet_tags = {tag.get("name", "").lower() for tag in pet.get("tags", [])}
                if not all(tag.lower() in pet_tags for tag in tags):
                    continue
            filtered_pets.append({
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name") if pet.get("category") else None,
                "status": pet.get("status"),
                "tags": [tag.get("name") for tag in pet.get("tags", [])] if pet.get("tags") else [],
                "photoUrls": pet.get("photoUrls", []),
            })

        _search_results_cache[search_id]["pets"] = filtered_pets
        _search_results_cache[search_id]["status"] = "completed"
        logger.info("Pet search completed for search_id=%s with %d results", search_id, len(filtered_pets))

    except Exception as e:
        logger.exception("Error processing pet search for search_id=%s", search_id)
        _search_results_cache[search_id]["status"] = "failed"
        _search_results_cache[search_id]["error"] = str(e)

@app.route("/pets/results/<search_id>", methods=["GET"])
async def pets_results(search_id):
    cache_entry = _search_results_cache.get(search_id)
    if not cache_entry:
        return jsonify({"error": "search_id not found"}), 404
    if cache_entry["status"] == "processing":
        return jsonify({"status": "processing"}), 202
    if cache_entry["status"] == "failed":
        return jsonify({"status": "failed", "error": cache_entry.get("error")}), 500
    return jsonify({"pets": cache_entry["pets"]})

@app.route("/pets/random-fact", methods=["POST"])
# workaround: validate_request after route for POST due to quart-schema defect
@validate_request(RandomFactRequest)
async def pets_random_fact(data: RandomFactRequest):
    try:
        import random
        fact = random.choice(_PREDEFINED_PET_FACTS)
        logger.info("Serving random pet fact")
        return jsonify({"fact": fact})
    except Exception as e:
        logger.exception("Error generating random pet fact")
        return jsonify({"error": "Failed to generate fact"}), 500

@app.before_serving
async def before_serving():
    logger.info("Starting Purrfect Pets API")

@app.after_serving
async def after_serving():
    await _async_client.aclose()
    logger.info("Shutting down Purrfect Pets API")

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)