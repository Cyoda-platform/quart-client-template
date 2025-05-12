```python
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for last fetched pets
last_fetched_pets: List[Dict[str, Any]] = []

# Simple in-memory job tracking for asynchronous processing
entity_job: Dict[str, Dict[str, Any]] = {}


async def fetch_pets_from_petstore(pet_type: str, status: str = None) -> List[Dict[str, Any]]:
    """
    Fetch pets from the Petstore API with optional filtering by type and status.
    Petstore API base: https://petstore.swagger.io/v2
    """
    url = "https://petstore.swagger.io/v2/pet/findByStatus"
    # Petstore API only supports filtering by status, not by type directly.
    # We will fetch by status and filter by type locally.
    # If status not provided, default to 'available' per Petstore docs.
    query_status = status if status else "available"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params={"status": query_status})
            response.raise_for_status()
            pets = response.json()
    except Exception as e:
        logger.exception(f"Failed to fetch pets from Petstore API: {e}")
        return []

    # Filter by type if specified and not "all"
    if pet_type and pet_type.lower() != "all":
        filtered = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == pet_type.lower()]
    else:
        filtered = pets

    # Normalize pet data fields as per response format in requirements
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
    """
    Simulate processing entity job that fetches pet data from Petstore API.
    Updates the in-memory cache after fetching.
    """
    try:
        pets = await fetch_pets_from_petstore(data.get("type", "all"), data.get("status"))
        global last_fetched_pets
        last_fetched_pets = pets
        entity_job[job_id]["status"] = "completed"
        entity_job[job_id]["resultCount"] = len(pets)
        entity_job[job_id]["completedAt"] = datetime.utcnow().isoformat()
        logger.info(f"Job {job_id} completed with {len(pets)} pets fetched.")
    except Exception as e:
        entity_job[job_id]["status"] = "failed"
        entity_job[job_id]["error"] = str(e)
        logger.exception(f"Job {job_id} failed: {e}")


@app.route("/pets/fetch", methods=["POST"])
async def pets_fetch():
    """
    POST /pets/fetch
    Body: { type: string, status: string (optional) }
    Fetch pet data from Petstore API and store it in local cache.
    """
    data = await request.get_json(force=True)
    pet_type = data.get("type", "all")
    status = data.get("status")

    job_id = f"job_{datetime.utcnow().timestamp()}"
    entity_job[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "type": pet_type,
        "statusFilter": status,
    }

    # Fire and forget the processing task
    asyncio.create_task(process_entity(job_id, data))

    return jsonify({"jobId": job_id, "status": "processing"}), 202


@app.route("/pets", methods=["GET"])
async def get_pets():
    """
    GET /pets
    Return the last fetched pet data.
    """
    return jsonify({"pets": last_fetched_pets})


@app.route("/pets/fun-fact", methods=["POST"])
async def pets_fun_fact():
    """
    POST /pets/fun-fact
    Body: { type: string }
    Return a fun pet fact or name.
    """
    data = await request.get_json(force=True)
    pet_type = data.get("type", "random").lower()

    # Simple hardcoded fun facts per pet type
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
    import random

    fact = random.choice(facts)

    return jsonify({"fact": fact})


if __name__ == "__main__":
    import sys

    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
