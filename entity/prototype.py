```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request, abort
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory async-safe cache for pets and jobs
class AsyncCache:
    def __init__(self):
        self._pets: Dict[int, Dict] = {}
        self._lock = asyncio.Lock()
        self._next_id = 1

    async def add_pets(self, pets: List[Dict]) -> int:
        async with self._lock:
            count = 0
            for pet in pets:
                pet_id = self._next_id
                pet['id'] = pet_id
                pet.setdefault("funFact", "")
                self._pets[pet_id] = pet
                self._next_id += 1
                count += 1
            return count

    async def list_pets(self) -> List[Dict]:
        async with self._lock:
            return list(self._pets.values())

    async def get_pet(self, pet_id: int) -> Optional[Dict]:
        async with self._lock:
            return self._pets.get(pet_id)

    async def update_funfact(self, pet_id: int, fun_fact: str) -> bool:
        async with self._lock:
            pet = self._pets.get(pet_id)
            if not pet:
                return False
            pet["funFact"] = fun_fact
            return True

pets_cache = AsyncCache()

# Job tracking for fetch tasks
entity_jobs: Dict[str, Dict] = {}
entity_jobs_lock = asyncio.Lock()

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

# Utility to add a simple fun fact per pet type
def generate_fun_fact(pet: Dict) -> str:
    # Simple static fun facts per type - extend as needed
    facts = {
        "dog": "Dogs have an incredible sense of smell!",
        "cat": "Cats sleep for 70% of their lives.",
        "bird": "Some birds can mimic human speech.",
        "rabbit": "Rabbits have nearly 360-degree panoramic vision.",
    }
    pet_type = pet.get("type", "").lower()
    return facts.get(pet_type, "This pet is a wonderful companion!")

async def fetch_petstore_pets(pet_type: str, limit: Optional[int]) -> List[Dict]:
    async with httpx.AsyncClient() as client:
        # Petstore API: /pet/findByStatus?status=available
        # The Petstore does not have a direct "type" filter; we'll fetch by status and filter manually.
        try:
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": "available"})
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(e)
            raise

    # Filter by petType if not "all"
    if pet_type.lower() != "all":
        filtered = []
        for pet in pets:
            # Petstore API pet "category" field contains the type under "name"
            category = pet.get("category")
            if category and category.get("name", "").lower() == pet_type.lower():
                filtered.append(pet)
        pets = filtered

    if limit:
        pets = pets[:limit]

    # Transform pets to simplified model + add funFact
    transformed = []
    for p in pets:
        pet_obj = {
            "name": p.get("name", "Unnamed"),
            "type": p.get("category", {}).get("name", "unknown"),
            "status": p.get("status", "unknown"),
            # funFact will be added below
        }
        pet_obj["funFact"] = generate_fun_fact(pet_obj)
        transformed.append(pet_obj)

    return transformed

async def process_fetch_pet_job(job_id: str, pet_type: str, limit: Optional[int]):
    try:
        pets = await fetch_petstore_pets(pet_type, limit)
        count = await pets_cache.add_pets(pets)
        async with entity_jobs_lock:
            entity_jobs[job_id]["status"] = "completed"
            entity_jobs[job_id]["fetchedCount"] = count
            entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
    except Exception as e:
        logger.exception(e)
        async with entity_jobs_lock:
            entity_jobs[job_id]["status"] = "failed"
            entity_jobs[job_id]["error"] = str(e)

@app.route("/pets/fetch", methods=["POST"])
async def pets_fetch():
    data = await request.get_json(force=True)
    pet_type = data.get("petType", "all")
    limit = data.get("limit")
    if limit is not None:
        try:
            limit = int(limit)
            if limit <= 0:
                limit = None
        except Exception:
            limit = None

    job_id = f"job_{datetime.utcnow().timestamp()}"
    async with entity_jobs_lock:
        entity_jobs[job_id] = {
            "status": "processing",
            "requestedAt": datetime.utcnow().isoformat(),
            "petType": pet_type,
            "limit": limit,
        }

    # Fire and forget the processing task
    asyncio.create_task(process_fetch_pet_job(job_id, pet_type, limit))

    return jsonify({
        "status": "success",
        "jobId": job_id,
        "message": f"Fetching pets of type '{pet_type}' started."
    })


@app.route("/pets", methods=["GET"])
async def pets_list():
    pets = await pets_cache.list_pets()
    return jsonify(pets)


@app.route("/pets/funfact", methods=["POST"])
async def pets_funfact():
    data = await request.get_json(force=True)
    pet_id = data.get("petId")
    fun_fact = data.get("funFact")
    if not isinstance(pet_id, int) or not isinstance(fun_fact, str) or not fun_fact.strip():
        abort(400, "Invalid petId or funFact")

    updated = await pets_cache.update_funfact(pet_id, fun_fact.strip())
    if not updated:
        abort(404, f"Pet with id {pet_id} not found")

    return jsonify({"status": "success", "message": "Fun fact updated"})


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def pet_detail(pet_id):
    pet = await pets_cache.get_pet(pet_id)
    if not pet:
        abort(404, f"Pet with id {pet_id} not found")
    return jsonify(pet)


if __name__ == '__main__':
    import sys
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        stream=sys.stdout,
    )

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
