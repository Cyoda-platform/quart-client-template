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

# In-memory async-safe cache simulation using asyncio.Lock
class AsyncCache:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._data = {}

    async def set(self, key, value):
        async with self._lock:
            self._data[key] = value

    async def get(self, key, default=None):
        async with self._lock:
            return self._data.get(key, default)

    async def clear(self):
        async with self._lock:
            self._data.clear()

# Cache keys
SEARCH_RESULTS_KEY = "latest_search_results"

cache = AsyncCache()

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

# Utility to fetch pets from Petstore API by filters
async def fetch_pets_from_petstore(filters: Dict) -> List[Dict]:
    async with httpx.AsyncClient() as client:
        try:
            # Petstore API does not support complex search via POST,
            # so we simulate filtering manually after fetching all available pets.
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": filters.get("status", "available")})
            resp.raise_for_status()
            pets = resp.json()
            # Filter by type and breed manually
            filtered = []
            for pet in pets:
                if filters.get("type") and pet.get("category", {}).get("name", "").lower() != filters["type"].lower():
                    continue
                if filters.get("breed") and pet.get("name", "").lower() != filters["breed"].lower():
                    # Note: Petstore API doesn't have breed field, so we use name as a proxy here.
                    continue
                filtered.append(pet)
            return filtered
        except Exception as e:
            logger.exception(f"Error fetching pets from external Petstore API: {e}")
            return []

# Utility to fetch pet details by ID
async def fetch_pet_details_from_petstore(pet_id: int) -> Optional[Dict]:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/{pet_id}")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.exception(f"Error fetching pet details from Petstore API for petId={pet_id}: {e}")
            return None

# Business logic task to process search and cache results
async def process_search_job(job_id: str, filters: Dict):
    logger.info(f"Processing search job {job_id} with filters {filters}")
    pets = await fetch_pets_from_petstore(filters)
    await cache.set(SEARCH_RESULTS_KEY, pets)
    logger.info(f"Search job {job_id} completed, cached {len(pets)} pets.")

# Business logic task to process pet details (optional cache could be added here if desired)
async def process_details_job(job_id: str, pet_id: int) -> Optional[Dict]:
    logger.info(f"Processing details job {job_id} for petId={pet_id}")
    pet_details = await fetch_pet_details_from_petstore(pet_id)
    # TODO: Could cache details if needed
    return pet_details

@app.route("/pets/search", methods=["POST"])
async def pets_search():
    try:
        filters = await request.get_json()
        # Validate filters dictionary keys if needed - skipped due to dynamic data

        job_id = datetime.utcnow().isoformat() + "_search"
        # Fire and forget processing task
        asyncio.create_task(process_search_job(job_id, filters))
        return jsonify({"jobId": job_id, "status": "processing"}), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to start search"}), 500

@app.route("/pets/results", methods=["GET"])
async def pets_results():
    try:
        results = await cache.get(SEARCH_RESULTS_KEY, [])
        # Format response to match functional requirements
        response_pets = []
        for pet in results:
            response_pets.append({
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name"),
                "breed": pet.get("name"),  # Petstore API has no breed, using name as placeholder
                "status": pet.get("status"),
                "photoUrls": pet.get("photoUrls", [])
            })
        return jsonify({"pets": response_pets})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve results"}), 500

@app.route("/pets/details", methods=["POST"])
async def pets_details():
    try:
        data = await request.get_json()
        pet_id = data.get("petId")
        if not isinstance(pet_id, int):
            return jsonify({"error": "petId must be an integer"}), 400

        # Process synchronously here to return results immediately (prototype)
        pet_details = await fetch_pet_details_from_petstore(pet_id)
        if not pet_details:
            return jsonify({"error": "Pet not found"}), 404

        response = {
            "id": pet_details.get("id"),
            "name": pet_details.get("name"),
            "type": pet_details.get("category", {}).get("name"),
            "breed": pet_details.get("name"),  # No breed info, reuse name
            "status": pet_details.get("status"),
            "photoUrls": pet_details.get("photoUrls", []),
            "description": pet_details.get("tags", [{}])[0].get("name", "")  # Using tags as description proxy
        }
        return jsonify(response)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pet details"}), 500

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
