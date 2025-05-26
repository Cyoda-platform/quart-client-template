import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Dataclasses for request validation
@dataclass
class FetchPets:
    status: Optional[str]
    type: Optional[str]
    sort: Optional[str]
    limit: Optional[int]

@dataclass
class FavoritePet:
    petId: int
    userId: str

# In-memory "storage"
pets_data = []
pets_data_lock = asyncio.Lock()
favorites: Dict[str, set] = {}
favorites_lock = asyncio.Lock()
entity_job: Dict[str, Dict[str, Any]] = {}
entity_job_lock = asyncio.Lock()

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"


async def fetch_pets_from_petstore(filter_params: Dict[str, Any]) -> list:
    status = filter_params.get("status", "available")
    limit = filter_params.get("limit", 50)
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": status})
            r.raise_for_status()
            pets = r.json()
        except Exception as e:
            logger.exception(e)
            return []
    pet_type = filter_params.get("type")
    if pet_type:
        pets = [p for p in pets if p.get("category") and p["category"].get("name", "").lower() == pet_type.lower()]
    sort_field = filter_params.get("sort")
    if sort_field:
        def sort_key(p):
            if sort_field == "name":
                return p.get("name", "")
            elif sort_field == "status":
                return p.get("status", "")
            elif sort_field == "type":
                return p.get("category", {}).get("name", "")
            return ""
        pets = sorted(pets, key=sort_key)
    pets = pets[:limit]
    return pets


async def process_fetch_job(job_id: str, filter_params: Dict[str, Any]):
    try:
        pets = await fetch_pets_from_petstore(filter_params)
        async with pets_data_lock:
            pets_data.clear()
            pets_data.extend(pets)
        async with entity_job_lock:
            entity_job[job_id].update({
                "status": "completed",
                "completedAt": datetime.utcnow().isoformat(),
                "count": len(pets)
            })
        logger.info(f"Fetch job {job_id} completed with {len(pets)} pets.")
    except Exception as e:
        async with entity_job_lock:
            entity_job[job_id].update({
                "status": "failed",
                "completedAt": datetime.utcnow().isoformat(),
                "error": str(e)
            })
        logger.exception(e)


@app.route('/purrfect-pets/fetch', methods=['POST'])
# Workaround: validate_request must come after @app.route for POST due to quart-schema defect
@validate_request(FetchPets)
async def fetch_pets(data: FetchPets):
    filter_params = {}
    if data.status: filter_params["status"] = data.status
    if data.type: filter_params["type"] = data.type
    job_id = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    async with entity_job_lock:
        entity_job[job_id] = {
            "status": "processing",
            "requestedAt": datetime.utcnow().isoformat(),
        }
    asyncio.create_task(process_fetch_job(job_id, {
        **filter_params,
        "sort": data.sort,
        "limit": data.limit
    }))
    return jsonify({
        "message": "Fetch job started",
        "jobId": job_id,
    })


@app.route('/purrfect-pets/list', methods=['GET'])
async def list_pets():
    async with pets_data_lock:
        pets_summary = [{
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name") if pet.get("category") else None,
            "status": pet.get("status"),
        } for pet in pets_data]
    return jsonify(pets_summary)


@app.route('/purrfect-pets/details/<int:pet_id>', methods=['GET'])
async def pet_details(pet_id: int):
    async with pets_data_lock:
        pet = next((p for p in pets_data if p.get("id") == pet_id), None)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404
    response = {
        "id": pet.get("id"),
        "name": pet.get("name"),
        "type": pet.get("category", {}).get("name") if pet.get("category") else None,
        "status": pet.get("status"),
        "photoUrls": pet.get("photoUrls", []),
        "tags": [tag.get("name") for tag in pet.get("tags", [])] if pet.get("tags") else [],
        "description": f"A lovely {pet.get('category', {}).get('name', 'pet')} named {pet.get('name')}.",  # TODO: real descriptions
    }
    return jsonify(response)


@app.route('/purrfect-pets/favorite', methods=['POST'])
# Workaround: validate_request must come after @app.route for POST due to quart-schema defect
@validate_request(FavoritePet)
async def favorite_pet(data: FavoritePet):
    pet_id = data.petId
    user_id = data.userId
    async with pets_data_lock:
        exists = any(p.get("id") == pet_id for p in pets_data)
    if not exists:
        return jsonify({"error": "Pet not found"}), 404
    async with favorites_lock:
        favorites.setdefault(user_id, set()).add(pet_id)
    return jsonify({"message": "Pet added to favorites"})


if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)