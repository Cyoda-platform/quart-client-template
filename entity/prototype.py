```python
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory async-safe cache for search results and pet details
# Structure:
#  search_cache: searchId -> {"status": str, "requestedAt": datetime, "results": List[dict]}
#  pet_details_cache: petId -> {"status": str, "requestedAt": datetime, "data": dict}
search_cache: Dict[str, Dict] = {}
pet_details_cache: Dict[int, Dict] = {}

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

# Utility function to generate unique IDs
def generate_id() -> str:
    return str(uuid.uuid4())


@app.route("/pets/search", methods=["POST"])
async def pets_search():
    """
    POST /pets/search
    Request JSON:
    {
      "status": "available|pending|sold",
      "category": "string (optional)"
    }
    Response JSON:
    {
      "searchId": "string"
    }
    """
    data = await request.get_json()
    status_filter = data.get("status")
    category_filter = data.get("category")

    search_id = generate_id()
    requested_at = datetime.utcnow()

    # Mark initial cache entry as processing
    search_cache[search_id] = {"status": "processing", "requestedAt": requested_at, "results": None}

    async def process_search():
        try:
            async with httpx.AsyncClient() as client:
                # Build query params for Petstore API
                params = {"status": status_filter} if status_filter else {}
                # Petstore API does not support category filter on /pet/findByStatus,
                # so we will filter results locally if category_filter provided.
                resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params=params)
                resp.raise_for_status()
                pets = resp.json()  # List of pet dicts

                if category_filter:
                    # Filter pets by category name (case-insensitive)
                    pets = [
                        pet for pet in pets
                        if pet.get("category") and pet["category"].get("name", "").lower() == category_filter.lower()
                    ]

                # Store minimal pet info with optional description placeholder
                results = []
                for pet in pets:
                    results.append({
                        "id": pet.get("id"),
                        "name": pet.get("name"),
                        "category": pet.get("category", {}).get("name"),
                        "status": pet.get("status"),
                        "description": None  # TODO: Petstore API does not provide description; placeholder None
                    })

                search_cache[search_id]["results"] = results
                search_cache[search_id]["status"] = "completed"
                logger.info(f"Search {search_id} completed with {len(results)} results.")
        except Exception as e:
            search_cache[search_id]["status"] = "failed"
            logger.exception(f"Failed processing search {search_id}: {e}")

    asyncio.create_task(process_search())

    return jsonify({"searchId": search_id})


@app.route("/pets/search/<string:search_id>", methods=["GET"])
async def get_search_results(search_id):
    """
    GET /pets/search/{searchId}
    Response JSON:
    {
      "searchId": "string",
      "results": [ ... ]
    }
    """
    entry = search_cache.get(search_id)
    if not entry:
        return jsonify({"error": "searchId not found"}), 404

    if entry["status"] == "processing":
        return jsonify({"searchId": search_id, "status": "processing", "results": None}), 202

    if entry["status"] == "failed":
        return jsonify({"searchId": search_id, "status": "failed", "results": None}), 500

    return jsonify({"searchId": search_id, "results": entry["results"]})


@app.route("/pets/details", methods=["POST"])
async def pets_details():
    """
    POST /pets/details
    Request JSON:
    {
      "petIds": [integer, integer, ...]
    }
    Response JSON:
    {
      "pets": [
        {
          "id": integer,
          "name": string,
          "category": string,
          "status": string,
          "funDescription": string
        },
        ...
      ]
    }
    """
    data = await request.get_json()
    pet_ids = data.get("petIds", [])
    if not isinstance(pet_ids, list) or not pet_ids:
        return jsonify({"error": "petIds must be a non-empty list"}), 400

    pets_response = []

    async def fetch_and_enrich_pet(pet_id: int):
        requested_at = datetime.utcnow()
        pet_details_cache[pet_id] = {"status": "processing", "requestedAt": requested_at, "data": None}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{PETSTORE_BASE_URL}/pet/{pet_id}")
                resp.raise_for_status()
                pet = resp.json()

                # Build funDescription - playful text based on pet's name and category
                name = pet.get("name", "Mysterious Pet")
                category = pet.get("category", {}).get("name", "Unknown Category")
                status = pet.get("status", "unknown")

                fun_description = f"{name} is a wonderful {category.lower()} currently {status} and waiting for a loving home! 😻"

                enriched = {
                    "id": pet_id,
                    "name": name,
                    "category": category,
                    "status": status,
                    "funDescription": fun_description,
                }

                pet_details_cache[pet_id]["data"] = enriched
                pet_details_cache[pet_id]["status"] = "completed"
                logger.info(f"Pet details for {pet_id} retrieved and enriched.")
                return enriched

        except Exception as e:
            pet_details_cache[pet_id]["status"] = "failed"
            logger.exception(f"Failed to fetch/enrich pet details for {pet_id}: {e}")
            return None

    # Fetch all pets concurrently
    tasks = [fetch_and_enrich_pet(pid) for pid in pet_ids]
    results = await asyncio.gather(*tasks)

    # Filter out None results (failed fetches)
    pets_response = [pet for pet in results if pet is not None]

    return jsonify({"pets": pets_response})


@app.route("/pets/details/<int:pet_id>", methods=["GET"])
async def get_pet_details(pet_id):
    """
    GET /pets/details/{petId}
    Response JSON:
    {
      "id": integer,
      "name": string,
      "category": string,
      "status": string,
      "funDescription": string
    }
    """
    entry = pet_details_cache.get(pet_id)
    if not entry:
        return jsonify({"error": "petId not found"}), 404

    if entry["status"] == "processing":
        return jsonify({"petId": pet_id, "status": "processing", "data": None}), 202

    if entry["status"] == "failed":
        return jsonify({"petId": pet_id, "status": "failed", "data": None}), 500

    return jsonify(entry["data"])


if __name__ == '__main__':
    import sys

    # Setup basic logging to stdout
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```