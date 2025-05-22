```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory "cache" for fetched pets and matches keyed by job_id
pets_cache: Dict[str, List[Dict]] = {}
matches_cache: Dict[str, List[Dict]] = {}


async def fetch_pets_from_petstore(pet_type: str, status: str, limit: Optional[int]) -> List[Dict]:
    """
    Fetch pets from the real Swagger Petstore API.
    The Petstore API: https://petstore3.swagger.io/api/v3/pet/findByStatus?status={status}
    
    Since the Petstore API doesn't support type filter directly, we filter client-side.
    """
    url = "https://petstore3.swagger.io/api/v3/pet/findByStatus"
    params = {"status": status} if status != "all" else {"status": "available"}  # fallback

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(f"Failed to fetch pets from Petstore API: {e}")
            return []

    # Filter by type if needed (pet_type is one of cat, dog, bird, all)
    # Petstore API uses category.name for type, but categories may be missing or empty.
    def pet_matches_type(pet):
        if pet_type == "all":
            return True
        categories = pet.get("category")
        if not categories:
            return False
        if isinstance(categories, dict):
            # category is an object {id, name}
            return categories.get("name", "").lower() == pet_type.lower()
        elif isinstance(categories, list):
            return any(cat.get("name", "").lower() == pet_type.lower() for cat in categories)
        return False

    filtered = [pet for pet in pets if pet_matches_type(pet)]
    if limit and limit > 0:
        filtered = filtered[:limit]

    # Normalize pets data for response
    normalized = []
    for pet in filtered:
        normalized.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name") if isinstance(pet.get("category"), dict) else None,
            "status": status,
            "photoUrls": pet.get("photoUrls", []),
        })
    return normalized


async def match_pets(preferences: Dict) -> List[Dict]:
    """
    Simple matching logic: fetch pets by status=available,
    filter by type, then return up to maxResults with a dummy matchScore.
    """
    pet_type = preferences.get("type", "all")
    max_results = preferences.get("maxResults", 10)
    # Use Petstore API status "available" for matches
    pets = await fetch_pets_from_petstore(pet_type, "available", max_results)

    # Assign dummy matchScore based on name length (just for demo)
    for pet in pets:
        pet["matchScore"] = min(1.0, len(pet.get("name") or "") / 10)

    return pets


@app.route("/pets/fetch", methods=["POST"])
async def pets_fetch():
    """
    POST /pets/fetch
    Body:
    {
      "type": "cat" | "dog" | "bird" | "all",
      "status": "available" | "pending" | "sold" | "all",
      "limit": int (optional)
    }
    """
    data = await request.get_json()
    pet_type = data.get("type", "all")
    status = data.get("status", "available")
    limit = data.get("limit")

    requested_at = datetime.utcnow().isoformat()
    job_id = f"fetch-{requested_at}"

    logger.info(f"Received fetch request: type={pet_type} status={status} limit={limit}")

    # Fire and forget fetch task, store pets in cache keyed by job_id
    async def process_fetch():
        pets = await fetch_pets_from_petstore(pet_type, status, limit)
        pets_cache[job_id] = pets
        logger.info(f"Fetch job {job_id} completed with {len(pets)} pets")

    asyncio.create_task(process_fetch())

    return jsonify({"jobId": job_id, "status": "processing", "requestedAt": requested_at})


@app.route("/pets/match", methods=["POST"])
async def pets_match():
    """
    POST /pets/match
    Body:
    {
      "preferences": {
        "type": "cat" | "dog" | "bird",
        "status": "available",
        "maxResults": int
      }
    }
    """
    data = await request.get_json()
    preferences = data.get("preferences", {})
    requested_at = datetime.utcnow().isoformat()
    job_id = f"match-{requested_at}"

    logger.info(f"Received match request: preferences={preferences}")

    async def process_match():
        matches = await match_pets(preferences)
        matches_cache[job_id] = matches
        logger.info(f"Match job {job_id} completed with {len(matches)} matches")

    asyncio.create_task(process_match())

    return jsonify({"jobId": job_id, "status": "processing", "requestedAt": requested_at})


@app.route("/pets", methods=["GET"])
async def get_pets():
    """
    GET /pets
    Returns all pets from all fetch jobs combined (mocked).
    """
    all_pets = []
    for pets_list in pets_cache.values():
        all_pets.extend(pets_list)

    return jsonify(all_pets)


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet_detail(pet_id: int):
    """
    GET /pets/{id}
    Returns detailed info for a single pet if found in cache.
    """
    # Search pet in cache
    for pets_list in pets_cache.values():
        for pet in pets_list:
            if pet.get("id") == pet_id:
                # Add optional description placeholder
                pet_detail = pet.copy()
                pet_detail["description"] = f"A lovely {pet_detail.get('type') or 'pet'} named {pet_detail.get('name')}."
                return jsonify(pet_detail)

    return jsonify({"error": "Pet not found"}), 404


if __name__ == '__main__':
    import sys

    logging.basicConfig(stream=sys.stdout,
                        format='%(asctime)s %(levelname)s %(message)s',
                        level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
