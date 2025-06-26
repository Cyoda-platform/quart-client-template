import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class FetchPetsRequest:
    type: Optional[str] = None
    status: Optional[str] = None

@dataclass
class GetPetsQuery:
    type: Optional[str] = None
    status: Optional[str] = None

@dataclass
class FunFactRequest:
    category: Optional[str] = None

# In-memory async-safe cache simulation
class AsyncCache:
    def __init__(self):
        self._pets: Dict[int, dict] = {}
        self._lock = asyncio.Lock()

    async def update_pets(self, pets: List[dict]):
        async with self._lock:
            for pet in pets:
                self._pets[pet["id"]] = pet

    async def get_all_pets(self, type_filter: Optional[str] = None, status_filter: Optional[str] = None) -> List[dict]:
        async with self._lock:
            pets = list(self._pets.values())
            if type_filter:
                pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == type_filter.lower()]
            if status_filter:
                pets = [p for p in pets if p.get("status") == status_filter]
            return pets

    async def get_pet(self, pet_id: int) -> Optional[dict]:
        async with self._lock:
            return self._pets.get(pet_id)

cache = AsyncCache()
entity_jobs: Dict[str, dict] = {}
PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"

async def fetch_pets_from_petstore(type_: Optional[str], status: Optional[str]) -> List[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            params = {}
            if status:
                params["status"] = status
            response = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params=params)
            response.raise_for_status()
            pets = response.json()
            if type_:
                pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == type_.lower()]
            return pets
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.exception(f"Error fetching pets from Petstore API: {e}")
            return []

async def process_fetch_pets_job(job_id: str, type_: Optional[str], status: Optional[str]):
    try:
        pets = await fetch_pets_from_petstore(type_, status)
        await cache.update_pets(pets)
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
        entity_jobs[job_id]["count"] = len(pets)
        logger.info(f"Fetched and stored {len(pets)} pets for job {job_id}")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        logger.exception(e)

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)  # workaround: validate_request last for POST methods due to quart-schema issue
async def pets_fetch(data: FetchPetsRequest):
    type_ = data.type
    status = data.status
    job_id = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
    }
    asyncio.create_task(process_fetch_pets_job(job_id, type_, status))
    return jsonify({"message": "Pets fetch started", "jobId": job_id}), 202

@validate_querystring(GetPetsQuery)  # workaround: validate_querystring first for GET due to quart-schema issue
@app.route("/pets", methods=["GET"])
async def pets_list():
    args = request.args
    type_filter = args.get("type")
    status_filter = args.get("status")
    pets = await cache.get_all_pets(type_filter, status_filter)
    pets_simple = [
        {
            "id": p.get("id"),
            "name": p.get("name"),
            "type": p.get("category", {}).get("name"),
            "status": p.get("status"),
        }
        for p in pets
    ]
    return jsonify(pets_simple)

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def pet_detail(pet_id: int):
    pet = await cache.get_pet(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404
    pet_detail_response = {
        "id": pet.get("id"),
        "name": pet.get("name"),
        "type": pet.get("category", {}).get("name"),
        "status": pet.get("status"),
        "photoUrls": pet.get("photoUrls", []),
        "tags": [tag.get("name") for tag in pet.get("tags", []) if "name" in tag],
    }
    return jsonify(pet_detail_response)

@app.route("/fun/random-fact", methods=["POST"])
@validate_request(FunFactRequest)  # workaround: validate_request last for POST methods due to quart-schema issue
async def fun_random_fact(data: FunFactRequest):
    import random
    # TODO: implement category-based fact selection if needed
    fact = random.choice(FUN_PET_FACTS)
    return jsonify({"fact": fact})

FUN_PET_FACTS = [
    "Cats sleep for 70% of their lives!",
    "Dogs have three eyelids.",
    "Rabbits can't vomit.",
    "Goldfish can see both infrared and ultraviolet light.",
    "Parrots will selflessly help each other out.",
]

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)