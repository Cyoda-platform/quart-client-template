import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data classes for request validation
@dataclass
class FetchPetsRequest:
    type: Optional[str] = None
    status: Optional[str] = None

@dataclass
class AddFavoriteRequest:
    pet_id: str

# In-memory caches
pets_cache: List[Dict] = []
favorites_cache: List[Dict] = []
entity_jobs: Dict[str, Dict] = {}

async def fetch_petstore_data(pet_type: Optional[str], status: Optional[str]) -> List[Dict]:
    url = "https://petstore.swagger.io/v2/pet/findByStatus"
    statuses = ["available", "pending", "sold"]
    if status and status.lower() in statuses:
        query_statuses = [status.lower()]
    else:
        query_statuses = statuses
    pets = []
    async with httpx.AsyncClient() as client:
        for s in query_statuses:
            try:
                resp = await client.get(url, params={"status": s}, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                pets.extend(data if isinstance(data, list) else [])
            except Exception as e:
                logger.exception(f"Error fetching pets for status={s}: {e}")
    if pet_type:
        pet_type_lower = pet_type.lower()
        pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == pet_type_lower]
    return pets

def enrich_pet_description(pet: Dict) -> str:
    pet_type = pet.get("category", {}).get("name", "pet").lower()
    status = pet.get("status", "unknown").lower()
    name = pet.get("name", "This pet")
    descriptions = {
        "dog": f"{name} is a loyal doggie who loves belly rubs!",
        "cat": f"{name} is a curious cat with nine lives and endless naps.",
        "bird": f"{name} sings sweet melodies all day long.",
    }
    return descriptions.get(pet_type, f"{name} is a wonderful {pet_type} currently {status}.")

async def process_fetch_job(job_id: str, pet_type: Optional[str], status: Optional[str]):
    try:
        pets_raw = await fetch_petstore_data(pet_type, status)
        pets_enriched = []
        for pet in pets_raw:
            pet_copy = pet.copy()
            pet_copy["description"] = enrich_pet_description(pet)
            pets_enriched.append(pet_copy)
        pets_cache.clear()
        pets_cache.extend(pets_enriched)
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
        entity_jobs[job_id]["count"] = len(pets_enriched)
        logger.info(f"Fetch job {job_id} completed with {len(pets_enriched)} pets.")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        logger.exception(f"Fetch job {job_id} failed.")

@app.route("/pets/fetch", methods=["POST"])
# Workaround: place validate_request last due to quart-schema POST annotation bug
@validate_request(FetchPetsRequest)
async def pets_fetch(data: FetchPetsRequest):
    pet_type = data.type
    status = data.status
    job_id = datetime.utcnow().isoformat()
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": job_id,
        "type": pet_type,
        "status_filter": status,
    }
    asyncio.create_task(process_fetch_job(job_id, pet_type, status))
    return jsonify({
        "message": "Pets data fetch started",
        "job_id": job_id,
        "status": "processing"
    })

@app.route("/pets", methods=["GET"])
async def get_all_pets():
    return jsonify(pets_cache)

@app.route("/favorites/add", methods=["POST"])
# Workaround: place validate_request last due to quart-schema POST annotation bug
@validate_request(AddFavoriteRequest)
async def add_favorite(data: AddFavoriteRequest):
    pet_id = data.pet_id
    pet = next((p for p in pets_cache if str(p.get("id")) == pet_id), None)
    if not pet:
        return jsonify({"message": "Pet not found"}), 404
    if any(str(fav.get("id")) == pet_id for fav in favorites_cache):
        return jsonify({"message": "Pet already in favorites"}), 200
    favorites_cache.append(pet)
    logger.info(f"Pet {pet_id} added to favorites.")
    return jsonify({"message": "Pet added to favorites"})

@app.route("/favorites", methods=["GET"])
async def get_favorites():
    return jsonify(favorites_cache)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)