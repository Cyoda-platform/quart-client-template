from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import asyncio
import logging
from datetime import datetime
import random

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

class PetDataStore:
    def __init__(self):
        self.last_fetched_pets: List[Dict[str, Any]] = []
        self.entity_job: Dict[str, Dict[str, Any]] = {}

pet_store = PetDataStore()

@dataclass
class FetchPetsRequest:
    type: str
    status: Optional[str] = None

@dataclass
class FunFactRequest:
    type: str

async def fetch_pets_from_petstore(pet_type: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
    url = "https://petstore.swagger.io/v2/pet/findByStatus"
    query_status = status if status else "available"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params={"status": query_status})
            response.raise_for_status()
            pets = response.json()
    except Exception as e:
        logger.exception(f"Failed to fetch pets from Petstore API: {e}")
        return []

    if pet_type and pet_type.lower() != "all":
        filtered = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == pet_type.lower()]
    else:
        filtered = pets

    normalized = []
    for pet in filtered:
        normalized.append(
            {
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name"),
                "status": pet.get("status"),
                "tags": [tag.get("name") for tag in pet.get("tags", []) if "name" in tag],
                "photoUrls": pet.get("photoUrls", []),
            }
        )
    return normalized

async def process_entity(job_id: str, data: Dict[str, Any]):
    try:
        pets = await fetch_pets_from_petstore(data.get("type", "all"), data.get("status"))
        pet_store.last_fetched_pets = pets
        pet_store.entity_job[job_id]["status"] = "completed"
        pet_store.entity_job[job_id]["resultCount"] = len(pets)
        pet_store.entity_job[job_id]["completedAt"] = datetime.utcnow().isoformat()
        logger.info(f"Job {job_id} completed with {len(pets)} pets fetched.")
    except Exception as e:
        pet_store.entity_job[job_id]["status"] = "failed"
        pet_store.entity_job[job_id]["error"] = str(e)
        logger.exception(f"Job {job_id} failed: {e}")

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)  # validation last in POST (workaround issue in quart-schema)
async def pets_fetch(data: FetchPetsRequest):
    job_id = f"job_{datetime.utcnow().timestamp()}"
    pet_store.entity_job[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "type": data.type,
        "statusFilter": data.status,
    }
    asyncio.create_task(process_entity(job_id, data.__dict__))
    return jsonify({"jobId": job_id, "status": "processing"}), 202

@app.route("/pets", methods=["GET"])
async def get_pets():
    # No validation needed for GET without parameters
    return jsonify({"pets": pet_store.last_fetched_pets})

@app.route("/pets/fun-fact", methods=["POST"])
@validate_request(FunFactRequest)  # validation last in POST (workaround issue in quart-schema)
async def pets_fun_fact(data: FunFactRequest):
    pet_type = data.type.lower()
    fun_facts = {
        "dog": [
            "Dogs have a sense of time and can miss you!",
            "Dogs' noses are wet to help absorb scent chemicals.",
        ],
        "cat": [
            "Cats sleep for 70% of their lives.",
            "Cats have five toes on their front paws, but only four on their back paws.",
        ],
        "random": [
            "Pets bring joy and reduce stress!",
            "Adopting a pet can save lives.",
        ],
    }
    facts = fun_facts.get(pet_type, fun_facts["random"])
    fact = random.choice(facts)
    return jsonify({"fact": fact})

if __name__ == "__main__":
    import sys

    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
