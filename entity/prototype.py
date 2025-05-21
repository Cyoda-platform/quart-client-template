import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data classes for request validation
@dataclass
class PetSearchRequest:
    type: Optional[str]
    status: Optional[str]
    tags: Optional[List[str]]

@dataclass
class AdoptionRequest:
    pet_id: int
    adopter_name: str
    contact_info: str

# In-memory async-safe caches
pets_search_cache: Dict[str, Dict[str, Any]] = {}
adoption_workflow_cache: Dict[str, Dict[str, Any]] = {}
pets_search_lock = asyncio.Lock()
adoption_lock = asyncio.Lock()

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"


async def fetch_pets_from_petstore(criteria: Dict[str, Any]) -> Any:
    async with httpx.AsyncClient() as client:
        status = criteria.get("status", "available")
        tags = criteria.get("tags", [])
        try:
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": status})
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(f"Error fetching pets from Petstore API: {e}")
            return []

    pet_type = criteria.get("type")
    filtered = []
    for pet in pets:
        if pet_type and pet.get("category", {}).get("name", "").lower() != pet_type.lower():
            continue
        if tags:
            pet_tags = {tag["name"].lower() for tag in pet.get("tags", [])}
            if not all(t.lower() in pet_tags for t in tags):
                continue
        filtered.append(pet)

    return filtered


async def process_pet_search_job(search_id: str, criteria: Dict[str, Any]):
    try:
        pets = await fetch_pets_from_petstore(criteria)
        async with pets_search_lock:
            pets_search_cache[search_id]["status"] = "completed"
            pets_search_cache[search_id]["pets"] = pets
            pets_search_cache[search_id]["count"] = len(pets)
            pets_search_cache[search_id]["completedAt"] = datetime.utcnow().isoformat()
    except Exception as e:
        logger.exception(f"Error processing pet search job {search_id}: {e}")
        async with pets_search_lock:
            pets_search_cache[search_id]["status"] = "failed"
            pets_search_cache[search_id]["error"] = str(e)


async def process_adoption_workflow(adoption_id: str, adoption_data: Dict[str, Any]):
    try:
        steps = [
            "application_received",
            "background_check",
            "adoption_approved",
            "pet_delivered",
            "completed",
        ]
        async with adoption_lock:
            adoption_workflow_cache[adoption_id]["status"] = "processing"
            adoption_workflow_cache[adoption_id]["steps_completed"] = []

        for step in steps:
            await asyncio.sleep(1)
            async with adoption_lock:
                adoption_workflow_cache[adoption_id]["steps_completed"].append(step)
                if step == "completed":
                    adoption_workflow_cache[adoption_id]["status"] = "completed"
                else:
                    adoption_workflow_cache[adoption_id]["status"] = step

    except Exception as e:
        logger.exception(f"Error in adoption workflow {adoption_id}: {e}")
        async with adoption_lock:
            adoption_workflow_cache[adoption_id]["status"] = "failed"
            adoption_workflow_cache[adoption_id]["error"] = str(e)


@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearchRequest)  # Workaround: validate_request after @app.route due to quart-schema defect
async def pets_search(data: PetSearchRequest):
    criteria = data.__dict__
    search_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()
    search_entry = {
        "status": "processing",
        "requestedAt": requested_at,
        "criteria": criteria,
        "pets": [],
        "count": 0,
    }
    async with pets_search_lock:
        pets_search_cache[search_id] = search_entry

    asyncio.create_task(process_pet_search_job(search_id, criteria))

    return jsonify({"search_id": search_id, "count": 0}), 202


@app.route("/pets/search/<search_id>", methods=["GET"])
async def get_pets_search_results(search_id):
    async with pets_search_lock:
        entry = pets_search_cache.get(search_id)
        if not entry:
            return jsonify({"error": "Search ID not found"}), 404
        if entry["status"] == "processing":
            return jsonify({"status": "processing"}), 202

        pets_resp = []
        for p in entry.get("pets", []):
            pets_resp.append(
                {
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "type": p.get("category", {}).get("name"),
                    "status": p.get("status"),
                    "tags": [t.get("name") for t in p.get("tags", [])] if p.get("tags") else [],
                }
            )
        return jsonify({"search_id": search_id, "pets": pets_resp})


@app.route("/adoptions", methods=["POST"])
@validate_request(AdoptionRequest)  # Workaround: validate_request after @app.route due to quart-schema defect
async def create_adoption(data: AdoptionRequest):
    adoption_id = str(uuid.uuid4())
    adoption_entry = {
        "status": "initiated",
        "requestedAt": datetime.utcnow().isoformat(),
        "pet_id": data.pet_id,
        "adopter_name": data.adopter_name,
        "contact_info": data.contact_info,
        "steps_completed": [],
    }
    async with adoption_lock:
        adoption_workflow_cache[adoption_id] = adoption_entry

    asyncio.create_task(process_adoption_workflow(adoption_id, data.__dict__))

    return jsonify({"adoption_id": adoption_id, "status": "initiated"}), 202


@app.route("/adoptions/<adoption_id>", methods=["GET"])
async def get_adoption_status(adoption_id):
    async with adoption_lock:
        adoption = adoption_workflow_cache.get(adoption_id)
        if not adoption:
            return jsonify({"error": "Adoption ID not found"}), 404
        return jsonify(
            {
                "adoption_id": adoption_id,
                "pet_id": adoption.get("pet_id"),
                "adopter_name": adoption.get("adopter_name"),
                "status": adoption.get("status"),
                "steps_completed": adoption.get("steps_completed", []),
            }
        )


if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)