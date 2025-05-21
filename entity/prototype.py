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

# In-memory cache for pets data and jobs, stored per app context to avoid globals
class AppState:
    def __init__(self):
        self.pets: Dict[int, Dict] = {}
        self.next_id: int = 1
        self.entity_jobs: Dict[str, Dict] = {}

app.state = AppState()

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

# Helper: enrich pet with fun fact (simple static facts for prototype)
fun_facts = [
    "Cats sleep 70% of their lives.",
    "Dogs have three eyelids.",
    "Goldfish can remember things for months.",
    "Rabbits can't vomit.",
    "Horses can sleep both lying down and standing up."
]

def generate_fun_fact(pet_name: Optional[str] = None) -> str:
    # TODO: Enhance with dynamic or contextual facts
    import random
    fact = random.choice(fun_facts)
    if pet_name:
        return f"{pet_name} is special because {fact}"
    return fact

async def fetch_pets_from_petstore(category: Optional[str], status: Optional[str]) -> List[Dict]:
    # Petstore API /pet/findByStatus supports status query param
    # category filtering isn't supported directly, so will filter locally if provided
    params = {}
    if status:
        params["status"] = status

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params=params)
            response.raise_for_status()
            pets_data = response.json()
        except Exception as e:
            logger.exception(e)
            return []

    if category:
        # The Petstore API returns pets with 'category': {'id':..., 'name': ...}
        pets_data = [
            pet for pet in pets_data
            if pet.get("category") and pet["category"].get("name", "").lower() == category.lower()
        ]

    return pets_data

async def process_fetch_pet_job(job_id: str, category: Optional[str], status: Optional[str]) -> None:
    try:
        pets_data = await fetch_pets_from_petstore(category, status)
        new_pets = {}
        for pet in pets_data:
            pet_id = app.state.next_id
            app.state.next_id += 1

            new_pets[pet_id] = {
                "id": pet_id,
                "name": pet.get("name", "Unknown"),
                "category": pet.get("category", {}).get("name", "Unknown"),
                "status": pet.get("status", "unknown"),
                "description": pet.get("description", ""),
                "funFact": generate_fun_fact(pet.get("name"))
            }
        app.state.pets.update(new_pets)
        app.state.entity_jobs[job_id]["status"] = "completed"
        app.state.entity_jobs[job_id]["fetchedCount"] = len(new_pets)
        logger.info(f"Fetch job {job_id} completed, {len(new_pets)} pets fetched.")
    except Exception as e:
        app.state.entity_jobs[job_id]["status"] = "failed"
        logger.exception(f"Fetch job {job_id} failed: {e}")

@app.route("/pets/fetch", methods=["POST"])
async def pets_fetch():
    data = await request.get_json(force=True)
    category = data.get("category")
    status = data.get("status")

    job_id = f"job-{datetime.utcnow().isoformat()}"

    app.state.entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat()
    }

    # Fire-and-forget processing job
    asyncio.create_task(process_fetch_pet_job(job_id, category, status))

    return jsonify({
        "message": f"Fetch job {job_id} started",
        "jobId": job_id
    }), 202

@app.route("/pets", methods=["GET"])
async def pets_list():
    # Return all cached pets
    pets_list = list(app.state.pets.values())
    return jsonify(pets_list)

@app.route("/pets/recommendation", methods=["POST"])
async def pets_recommendation():
    data = await request.get_json(force=True)
    category = data.get("category")

    # Filter pets by category if provided
    filtered_pets = [
        pet for pet in app.state.pets.values()
        if category is None or pet["category"].lower() == category.lower()
    ]

    if not filtered_pets:
        return jsonify({"message": "No pets available for recommendation"}), 404

    import random
    pet = random.choice(filtered_pets)

    # TODO: Can enhance funFact dynamically here if needed
    response = {
        "id": pet["id"],
        "name": pet["name"],
        "category": pet["category"],
        "status": pet["status"],
        "funFact": pet.get("funFact", generate_fun_fact(pet["name"]))
    }
    return jsonify(response)

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def pet_detail(pet_id):
    pet = app.state.pets.get(pet_id)
    if not pet:
        return jsonify({"message": "Pet not found"}), 404
    return jsonify(pet)

if __name__ == '__main__':
    import sys
    import logging

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
