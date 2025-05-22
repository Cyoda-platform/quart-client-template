from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

pets_cache: Dict[int, dict] = {}
adoption_requests: Dict[str, dict] = {}
entity_jobs: Dict[str, dict] = {}

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

@dataclass
class FetchPetsRequest:
    filters: dict
    sortBy: Optional[str]
    limit: int

@dataclass
class AdoptionRequest:
    petId: int
    userName: str
    userEmail: str

async def fetch_external_pets(
    status_filter: Optional[str], type_filter: Optional[str], limit: int
) -> List[dict]:
    pets = []
    async with httpx.AsyncClient(timeout=10) as client:
        statuses = status_filter if status_filter else "available,pending,sold"
        params = {"status": statuses}
        try:
            r = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params=params)
            r.raise_for_status()
            all_pets = r.json()
            if type_filter:
                for pet in all_pets:
                    pet_type = pet.get("category", {}).get("name", "").lower()
                    if pet_type == type_filter.lower():
                        pets.append(pet)
                    if len(pets) >= limit:
                        break
            else:
                pets = all_pets[:limit]
        except Exception as e:
            logger.exception("Failed to fetch pets from external API")
            raise e
    return pets

async def process_and_cache_pets(
    filters: dict, sort_by: Optional[str], limit: int, job_id: str
) -> None:
    try:
        status_filter = filters.get("status") if filters else None
        type_filter = filters.get("type") if filters else None

        pets = await fetch_external_pets(status_filter, type_filter, limit)

        def pet_sort_key(p):
            if sort_by == "name":
                return p.get("name", "").lower()
            return 0

        if sort_by in ("name",):
            pets.sort(key=pet_sort_key)

        pets_cache.clear()
        for pet in pets:
            pets_cache[pet["id"]] = {
                "id": pet["id"],
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name", "unknown"),
                "status": pet.get("status"),
                "age": None,  # TODO: Placeholder for age
                "description": pet.get("description", ""),
                "photos": pet.get("photoUrls", []),
            }

        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["count"] = len(pets_cache)
        entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
        logger.info(f"Pets data fetched and cached successfully, count={len(pets_cache)}")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        logger.exception("Error processing pets data")

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)  # Workaround: validation last for POST due to quart_schema issue
async def fetch_pets(data: FetchPetsRequest):
    filters = data.filters
    sort_by = data.sortBy
    limit = data.limit
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        limit = 50

    job_id = datetime.utcnow().isoformat() + "-" + str(id(data))
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
    }

    asyncio.create_task(process_and_cache_pets(filters, sort_by, limit, job_id))

    return jsonify({
        "message": "Pets data fetching started",
        "jobId": job_id,
        "status": entity_jobs[job_id]["status"],
    })

@app.route("/pets", methods=["GET"])
async def get_pets():
    pets_list = []
    for pet in pets_cache.values():
        pets_list.append({
            "id": pet["id"],
            "name": pet["name"],
            "type": pet["type"],
            "status": pet["status"],
            "age": pet["age"],
        })
    return jsonify(pets_list)

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet_details(pet_id: int):
    pet = pets_cache.get(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404
    return jsonify(pet)

@app.route("/adoptions", methods=["POST"])
@validate_request(AdoptionRequest)  # Workaround: validation last for POST due to quart_schema issue
async def create_adoption(data: AdoptionRequest):
    pet_id = data.petId
    user_name = data.userName
    user_email = data.userEmail
    if pet_id not in pets_cache:
        return jsonify({"error": "Pet not found"}), 404

    request_id = f"req-{datetime.utcnow().timestamp()}-{pet_id}"
    adoption_requests[request_id] = {
        "requestId": request_id,
        "petId": pet_id,
        "user": {"name": user_name, "email": user_email},
        "status": "submitted",
        "submittedAt": datetime.utcnow().isoformat(),
    }

    logger.info(f"Adoption request submitted: {request_id} for pet {pet_id} by {user_name}")

    return jsonify({"message": "Adoption request submitted successfully", "requestId": request_id})

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)