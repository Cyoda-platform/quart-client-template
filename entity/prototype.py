import asyncio
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class PetSearchFilters:
    type: Optional[str] = None
    status: Optional[str] = None
    breed: Optional[str] = None

@dataclass
class PetDetailsRequest:
    petId: int

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

SEARCH_RESULTS_KEY = "latest_search_results"
cache = AsyncCache()
PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

async def fetch_pets_from_petstore(filters: Dict) -> List[Dict]:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": filters.get("status", "available")})
            resp.raise_for_status()
            pets = resp.json()
            filtered = []
            for pet in pets:
                if filters.get("type") and pet.get("category", {}).get("name", "").lower() != filters["type"].lower():
                    continue
                if filters.get("breed") and pet.get("name", "").lower() != filters["breed"].lower():
                    continue
                filtered.append(pet)
            return filtered
        except Exception as e:
            logger.exception(f"Error fetching pets from external Petstore API: {e}")
            return []

async def fetch_pet_details_from_petstore(pet_id: int) -> Optional[Dict]:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/{pet_id}")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.exception(f"Error fetching pet details from Petstore API for petId={pet_id}: {e}")
            return None

async def process_search_job(job_id: str, filters: Dict):
    logger.info(f"Processing search job {job_id} with filters {filters}")
    pets = await fetch_pets_from_petstore(filters)
    await cache.set(SEARCH_RESULTS_KEY, pets)
    logger.info(f"Search job {job_id} completed, cached {len(pets)} pets.")

async def process_details_job(job_id: str, pet_id: int) -> Optional[Dict]:
    logger.info(f"Processing details job {job_id} for petId={pet_id}")
    pet_details = await fetch_pet_details_from_petstore(pet_id)
    return pet_details

@app.route("/pets/search", methods=["POST"])
# Workaround: validate_request must follow route decorator for POST due to quart-schema defect
@validate_request(PetSearchFilters)
async def pets_search(data: PetSearchFilters):
    filters = data.__dict__
    job_id = datetime.utcnow().isoformat() + "_search"
    asyncio.create_task(process_search_job(job_id, filters))
    return jsonify({"jobId": job_id, "status": "processing"}), 202

@app.route("/pets/results", methods=["GET"])
async def pets_results():
    try:
        results = await cache.get(SEARCH_RESULTS_KEY, [])
        response_pets = []
        for pet in results:
            response_pets.append({
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name"),
                "breed": pet.get("name"),
                "status": pet.get("status"),
                "photoUrls": pet.get("photoUrls", [])
            })
        return jsonify({"pets": response_pets})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve results"}), 500

@app.route("/pets/details", methods=["POST"])
# Workaround: validate_request must follow route decorator for POST due to quart-schema defect
@validate_request(PetDetailsRequest)
async def pets_details(data: PetDetailsRequest):
    pet_id = data.petId
    pet_details = await fetch_pet_details_from_petstore(pet_id)
    if not pet_details:
        return jsonify({"error": "Pet not found"}), 404
    response = {
        "id": pet_details.get("id"),
        "name": pet_details.get("name"),
        "type": pet_details.get("category", {}).get("name"),
        "breed": pet_details.get("name"),
        "status": pet_details.get("status"),
        "photoUrls": pet_details.get("photoUrls", []),
        "description": pet_details.get("tags", [{}])[0].get("name", "")
    }
    return jsonify(response)

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)