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

# In-memory async-safe cache for pets and orders keyed by job or id
pets_cache: Dict[str, List[Dict]] = {}
orders_cache: Dict[int, Dict] = {}

# Petstore API base URL
PETSTORE_BASE = "https://petstore.swagger.io/v2"

# Simple utility to generate unique job ids and order ids
_job_counter = 0
_order_counter = 0
_job_lock = asyncio.Lock()
_order_lock = asyncio.Lock()


async def generate_job_id() -> str:
    global _job_counter
    async with _job_lock:
        _job_counter += 1
        return f"job-{_job_counter}"


async def generate_order_id() -> int:
    global _order_counter
    async with _order_lock:
        _order_counter += 1
        return _order_counter


def enrich_pet(pet: Dict) -> Dict:
    """Add a funFact field to pet data (simple static enrichment)."""
    fun_facts = [
        "Loves chasing laser pointers",
        "Enjoys naps in the sun",
        "Is a picky eater",
        "Has a secret stash of toys",
        "Can do a cute trick"
    ]
    # Simple deterministic enrichment based on pet id
    idx = pet.get("id", 0) % len(fun_facts)
    pet["funFact"] = fun_facts[idx]
    return pet


async def fetch_pets_from_petstore(status: Optional[str], tags: Optional[List[str]]) -> List[Dict]:
    """Fetch pets from Petstore API filtered by status and tags."""
    async with httpx.AsyncClient() as client:
        url = f"{PETSTORE_BASE}/pet/findByStatus"
        params = {}
        if status:
            params["status"] = status
        # Petstore API does not filter by tags, so we filter manually after fetch
        try:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception("Failed to fetch pets from Petstore API")
            pets = []

    if tags:
        tags_set = set(tags)
        filtered = []
        for pet in pets:
            pet_tags = set(t["name"] for t in pet.get("tags", []))
            if tags_set.intersection(pet_tags):
                filtered.append(pet)
        pets = filtered

    # Enrich pets with fun facts
    pets = [enrich_pet(pet) for pet in pets]
    return pets


async def process_pets_fetch(job_id: str, status: Optional[str], tags: Optional[List[str]]):
    """Background task to fetch and store pets."""
    try:
        logger.info(f"Starting pet fetch job {job_id} with status={status} tags={tags}")
        pets = await fetch_pets_from_petstore(status, tags)
        pets_cache[job_id] = pets
        logger.info(f"Completed pet fetch job {job_id}, fetched {len(pets)} pets")
    except Exception as e:
        logger.exception(f"Error processing pet fetch job {job_id}: {e}")
        pets_cache[job_id] = []


async def validate_pet_availability(pet_id: int) -> bool:
    """Check with Petstore API if pet is available (status == 'available')."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PETSTORE_BASE}/pet/{pet_id}", timeout=10)
            resp.raise_for_status()
            pet = resp.json()
            return pet.get("status") == "available"
        except Exception as e:
            logger.exception(f"Failed to validate pet availability for petId={pet_id}")
            return False


@app.route("/pets/fetch", methods=["POST"])
async def pets_fetch():
    data = await request.get_json()
    status = data.get("status")
    tags = data.get("tags")
    if tags is not None and not isinstance(tags, list):
        return jsonify({"error": "tags must be a list"}), 400

    job_id = await generate_job_id()
    # Fire and forget the processing task
    asyncio.create_task(process_pets_fetch(job_id, status, tags))

    return jsonify({"message": "Pets fetch started", "jobId": job_id})


@app.route("/pets", methods=["GET"])
async def pets_get():
    # Return all cached pets from all jobs merged, newest last job only?
    # For prototype, we return pets from the last job issued.
    if not pets_cache:
        return jsonify([])

    # Get the last job id by numeric part
    last_job_id = max(pets_cache.keys(), key=lambda k: int(k.split("-")[1]))
    pets = pets_cache.get(last_job_id, [])
    return jsonify(pets)


@app.route("/orders/create", methods=["POST"])
async def orders_create():
    data = await request.get_json()
    pet_id = data.get("petId")
    quantity = data.get("quantity", 1)
    ship_date = data.get("shipDate")
    complete = data.get("complete", False)

    if not isinstance(pet_id, int):
        return jsonify({"error": "petId must be an integer"}), 400

    # Validate pet availability
    available = await validate_pet_availability(pet_id)
    if not available:
        return jsonify({"error": "Pet is not available"}), 400

    order_id = await generate_order_id()
    order = {
        "orderId": order_id,
        "petId": pet_id,
        "quantity": quantity,
        "shipDate": ship_date,
        "complete": complete,
        "status": "placed",
        "createdAt": datetime.utcnow().isoformat() + "Z",
    }
    orders_cache[order_id] = order
    return jsonify({"orderId": order_id, "status": "placed"})


@app.route("/orders/<int:order_id>", methods=["GET"])
async def orders_get(order_id: int):
    order = orders_cache.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    return jsonify(order)


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
