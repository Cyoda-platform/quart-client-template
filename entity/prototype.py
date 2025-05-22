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

# Local in-memory cache to store the last fetched/enhanced pets data per "session"
# Key: job_id (str), Value: dict with keys: status:str, requestedAt:str, pets:List[Dict]
entity_job: Dict[str, Dict] = {}

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"


async def fetch_pets_from_petstore(
    status: Optional[str] = None, pet_type: Optional[str] = None
) -> List[Dict]:
    """
    Fetch pets from Petstore API filtered by status.
    Petstore API endpoint: GET /pet/findByStatus?status=available
    Note: Petstore API does not filter by type; type filtering is done later.
    """
    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
    params = {}
    if status:
        params["status"] = status
    else:
        # Default to available if no status given (Petstore requires status param)
        params["status"] = "available"

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(f"Error fetching pets from Petstore API: {e}")
            return []

    # Filter by pet_type if provided (Petstore API doesn't provide direct type filter)
    if pet_type:
        pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == pet_type.lower()]

    return pets


def add_personality_traits(pets: List[Dict]) -> List[Dict]:
    """
    Add fun personality traits to pets based on type or random logic.
    This is a simple mock enhancement.
    """
    personality_map = {
        "cat": [
            "playful and curious",
            "lazy and cuddly",
            "mischievous and clever",
            "independent and mysterious",
        ],
        "dog": [
            "friendly and loyal",
            "energetic and goofy",
            "calm and protective",
            "eager and attentive",
        ],
    }

    import random

    enhanced_pets = []
    for pet in pets:
        pet_copy = pet.copy()
        pet_type = pet_copy.get("category", {}).get("name", "").lower()
        if pet_type in personality_map:
            pet_copy["personality"] = random.choice(personality_map[pet_type])
        else:
            pet_copy["personality"] = "adorable and unique"
        enhanced_pets.append(pet_copy)

    return enhanced_pets


async def process_entity(job_id: str, filter_data: dict, enhance: bool):
    """
    Fire-and-forget task to fetch & optionally enhance pets data,
    then store results in `entity_job`.
    """
    try:
        pets = await fetch_pets_from_petstore(
            status=filter_data.get("status"), pet_type=filter_data.get("type")
        )
        logger.info(f"Fetched {len(pets)} pets from Petstore for job {job_id}")

        if enhance:
            pets = add_personality_traits(pets)
            logger.info(f"Enhanced pets with personality traits for job {job_id}")

        # Store results
        entity_job[job_id]["pets"] = pets
        entity_job[job_id]["status"] = "done"
        logger.info(f"Job {job_id} completed with {len(pets)} pets")
    except Exception as e:
        logger.exception(f"Error processing job {job_id}: {e}")
        entity_job[job_id]["status"] = "error"
        entity_job[job_id]["pets"] = []


@app.route("/pets/fetch", methods=["POST"])
async def pets_fetch():
    """
    POST /pets/fetch
    Request JSON:
    {
      "filter": {
        "status": "available",  // optional
        "type": "cat"           // optional
      },
      "enhance": true           // optional, default False
    }
    Response JSON:
    {
      "job_id": "string",
      "status": "processing"
    }
    """
    data = await request.get_json(force=True)
    filter_data = data.get("filter", {})
    enhance = data.get("enhance", False)

    job_id = datetime.utcnow().isoformat() + "-" + str(id(data))  # simple unique job id

    entity_job[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "pets": [],
    }

    # Fire and forget the processing task
    asyncio.create_task(process_entity(job_id, filter_data, enhance))

    return jsonify({"job_id": job_id, "status": "processing"}), 202


@app.route("/pets", methods=["GET"])
async def pets_get():
    """
    GET /pets?job_id=string
    Query param:
      job_id: string, required - to get the last fetched/enhanced pets for this job
    Response JSON:
    {
      "status": "processing|done|error",
      "pets": [ ... ]  // empty if processing or error
    }
    """
    job_id = request.args.get("job_id")
    if not job_id or job_id not in entity_job:
        return jsonify({"error": "job_id missing or not found"}), 400

    job_data = entity_job[job_id]
    return jsonify({"status": job_data["status"], "pets": job_data.get("pets", [])})


@app.route("/pets/filter", methods=["POST"])
async def pets_filter():
    """
    POST /pets/filter
    Request JSON:
    {
      "job_id": "string",  // required; which stored pets to filter
      "filter": {
        "type": "dog",          // optional
        "status": "available",  // optional
        "personality": "friendly" // optional keyword search in personality
      }
    }
    Response JSON:
    {
      "pets": [ ... filtered pets ... ]
    }
    """
    data = await request.get_json(force=True)
    job_id = data.get("job_id")
    if not job_id or job_id not in entity_job:
        return jsonify({"error": "job_id missing or not found"}), 400

    pets = entity_job[job_id].get("pets", [])
    if entity_job[job_id]["status"] != "done":
        return jsonify({"error": "pets data not ready"}), 400

    filters = data.get("filter", {})

    def matches_filter(pet: dict) -> bool:
        # type filter
        pet_type = pet.get("category", {}).get("name", "").lower()
        if filters.get("type") and filters["type"].lower() != pet_type:
            return False

        # status filter
        pet_status = pet.get("status", "").lower()
        if filters.get("status") and filters["status"].lower() != pet_status:
            return False

        # personality filter (keyword search)
        personality = pet.get("personality", "").lower()
        if filters.get("personality") and filters["personality"].lower() not in personality:
            return False

        return True

    filtered_pets = [pet for pet in pets if matches_filter(pet)]

    return jsonify({"pets": filtered_pets})


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
