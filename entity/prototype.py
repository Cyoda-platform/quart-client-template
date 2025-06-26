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
                pets = [p for p in pets if p.get("type") == type_filter]
            if status_filter:
                pets = [p for p in pets if p.get("status") == status_filter]
            return pets

    async def get_pet(self, pet_id: int) -> Optional[dict]:
        async with self._lock:
            return self._pets.get(pet_id)


cache = AsyncCache()

# Entity job registry to track async fetch
entity_jobs: Dict[str, dict] = {}

PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"

# Helper to fetch pets from Petstore API with filters
async def fetch_pets_from_petstore(type_: Optional[str], status: Optional[str]) -> List[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            params = {}
            if status:
                params["status"] = status
            # Petstore API does not support filtering by type in query param, so we fetch all filtered by status only
            response = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params=params)
            response.raise_for_status()
            pets = response.json()
            # Filter by type locally if needed
            if type_:
                pets = [p for p in pets if p.get("category", {}).get("name","").lower() == type_.lower()]
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
async def pets_fetch():
    data = await request.get_json(force=True)
    type_ = data.get("type")
    status = data.get("status")
    job_id = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
    }
    # Fire and forget
    asyncio.create_task(process_fetch_pets_job(job_id, type_, status))
    return jsonify({"message": "Pets fetch started", "jobId": job_id}), 202

@app.route("/pets", methods=["GET"])
async def pets_list():
    type_filter = request.args.get("type")
    status_filter = request.args.get("status")
    pets = await cache.get_all_pets(type_filter, status_filter)
    # Trim response to essential fields per spec
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
    # Compose detailed response
    pet_detail_response = {
        "id": pet.get("id"),
        "name": pet.get("name"),
        "type": pet.get("category", {}).get("name"),
        "status": pet.get("status"),
        "photoUrls": pet.get("photoUrls", []),
        "tags": [tag.get("name") for tag in pet.get("tags", []) if "name" in tag],
    }
    return jsonify(pet_detail_response)

# Static list of fun pet facts (could be replaced by external API)
FUN_PET_FACTS = [
    "Cats sleep for 70% of their lives!",
    "Dogs have three eyelids.",
    "Rabbits can't vomit.",
    "Goldfish can see both infrared and ultraviolet light.",
    "Parrots will selflessly help each other out.",
]

@app.route("/fun/random-fact", methods=["POST"])
async def fun_random_fact():
    # TODO: Replace with external fun fact API if desired
    import random
    fact = random.choice(FUN_PET_FACTS)
    return jsonify({"fact": fact})


if __name__ == "__main__":
    import sys
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
