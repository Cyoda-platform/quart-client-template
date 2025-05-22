import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any

import httpx
from quart import Quart, request, jsonify, abort
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Request/Query dataclasses
@dataclass
class FetchPets:
    type: Optional[str] = None
    status: Optional[str] = None

@dataclass
class RecommendPets:
    preferredType: Optional[str] = None
    maxResults: int = 3

@dataclass
class QueryPets:
    type: Optional[str] = None
    status: Optional[str] = None

# In-memory local cache for pets data.
pets_cache: Dict[int, Dict[str, Any]] = {}
entity_job: Dict[str, Dict[str, Any]] = {}
PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

def gen_job_id() -> str:
    return datetime.utcnow().isoformat(timespec='milliseconds').replace(":", "-")

async def fetch_pets_from_petstore(type_: Optional[str], status: Optional[str]) -> List[Dict[str, Any]]:
    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
    status_query = status if status else "available"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params={"status": status_query})
            r.raise_for_status()
            pets = r.json()
    except Exception as e:
        logger.exception("Failed to fetch pets from Petstore API")
        raise
    if type_:
        pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == type_.lower()]
    return pets

async def process_entity(job_id: str, type_: Optional[str], status: Optional[str]) -> None:
    try:
        pets = await fetch_pets_from_petstore(type_, status)
        for pet in pets:
            pet_id = pet.get("id")
            if pet_id is not None:
                pet.setdefault("description", f"A lovely {pet.get('category', {}).get('name', 'pet')}.")
                pets_cache[pet_id] = pet
        entity_job[job_id]["status"] = "completed"
        entity_job[job_id]["count"] = len(pets)
        entity_job[job_id]["completedAt"] = datetime.utcnow().isoformat()
        logger.info(f"Job {job_id} completed: {len(pets)} pets cached.")
    except Exception as e:
        entity_job[job_id]["status"] = "failed"
        entity_job[job_id]["error"] = str(e)
        logger.exception(f"Job {job_id} failed.")

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPets)  # workaround: validation last for POST due to quart-schema defect
async def pets_fetch(data: FetchPets):
    job_id = gen_job_id()
    entity_job[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "type": data.type,
        "status_filter": data.status,
    }
    asyncio.create_task(process_entity(job_id, data.type, data.status))
    return jsonify({
        "message": "Pets data fetch started.",
        "job_id": job_id,
    })

@validate_querystring(QueryPets)  # workaround: validation first for GET due to quart-schema defect
@app.route("/pets", methods=["GET"])
async def pets_list():
    type_filter = request.args.get("type")
    status_filter = request.args.get("status")
    def pet_matches(pet: Dict[str, Any]) -> bool:
        if type_filter:
            if pet.get("category", {}).get("name", "").lower() != type_filter.lower():
                return False
        if status_filter:
            if pet.get("status", "").lower() != status_filter.lower():
                return False
        return True
    filtered_pets = [pet for pet in pets_cache.values() if pet_matches(pet)]
    response = []
    for pet in filtered_pets:
        response.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name"),
            "status": pet.get("status"),
            "tags": [tag.get("name") for tag in pet.get("tags", []) if "name" in tag] if pet.get("tags") else [],
            "photoUrls": pet.get("photoUrls", []),
        })
    return jsonify(response)

@app.route("/pets/recommend", methods=["POST"])
@validate_request(RecommendPets)  # workaround: validation last for POST due to quart-schema defect
async def pets_recommend(data: RecommendPets):
    preferred_type = data.preferredType
    max_results = data.maxResults
    candidates = []
    for pet in pets_cache.values():
        if preferred_type:
            if pet.get("category", {}).get("name", "").lower() != preferred_type.lower():
                continue
        candidates.append(pet)
    if preferred_type and not candidates:
        candidates = list(pets_cache.values())
    recommended = candidates[:max_results]
    response = []
    for pet in recommended:
        response.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name"),
            "status": pet.get("status"),
            "funFact": f"{pet.get('name')} loves to play and cuddle! 😸",  # TODO: Replace with real fun facts
        })
    return jsonify(response)

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def pet_detail(pet_id: int):
    pet = pets_cache.get(pet_id)
    if not pet:
        abort(404, description=f"Pet with id {pet_id} not found in cache.")
    return jsonify({
        "id": pet.get("id"),
        "name": pet.get("name"),
        "type": pet.get("category", {}).get("name"),
        "status": pet.get("status"),
        "tags": [tag.get("name") for tag in pet.get("tags", []) if "name" in tag] if pet.get("tags") else [],
        "photoUrls": pet.get("photoUrls", []),
        "description": pet.get("description"),
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)