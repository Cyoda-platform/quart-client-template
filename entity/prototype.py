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

# In-memory cache for pets data and job statuses
# Structure:
#   pets_data: List[Dict] - stored enriched pets
#   entity_jobs: Dict[str, Dict] - job_id -> job info/status
pets_data: List[Dict] = []
entity_jobs: Dict[str, Dict] = {}


# Constants
PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"


async def fetch_pets_from_petstore(
    status: Optional[str], pet_type: Optional[str], limit: int
) -> List[Dict]:
    """Fetch pets from external Petstore API with optional filtering."""
    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
    params = {}

    # Petstore supports status as a comma-separated string, so we send if status provided
    if status:
        params["status"] = status
    else:
        # Default to all statuses if none provided (Petstore requires status param)
        params["status"] = "available,pending,sold"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            pets = response.json()
    except Exception as e:
        logger.exception("Failed to fetch pets from Petstore API")
        raise

    # Filter by pet_type if specified (Petstore does not support type filtering)
    if pet_type:
        pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == pet_type.lower()]

    # Limit results
    pets = pets[:limit]

    return pets


def enrich_pet_description(pet: Dict) -> str:
    """Generate a playful description for a pet."""
    name = pet.get("name", "Unnamed")
    pet_type = pet.get("category", {}).get("name", "pet").lower()
    status = pet.get("status", "unknown")

    # Simple playful message
    description = f"{name} is a lovely {pet_type} currently {status}."
    if pet_type == "cat":
        description += " Loves naps and chasing yarn balls! 😸"
    elif pet_type == "dog":
        description += " Always ready for a walk and lots of belly rubs! 🐶"
    else:
        description += " A wonderful companion waiting for you!"

    return description


async def process_entity(entity_job: Dict, params: Dict):
    """Background task to fetch, enrich, and store pets."""
    try:
        pets = await fetch_pets_from_petstore(
            status=params.get("status"),
            pet_type=params.get("type"),
            limit=params.get("limit", 10),
        )
        enriched_pets = []
        for pet in pets:
            enriched_pets.append(
                {
                    "id": pet.get("id"),
                    "name": pet.get("name"),
                    "type": pet.get("category", {}).get("name", "").lower(),
                    "status": pet.get("status"),
                    "description": enrich_pet_description(pet),
                }
            )

        # Update pets_data atomically
        # TODO: If concurrency issues arise, consider locks or other concurrency-safe approaches
        pets_data.clear()
        pets_data.extend(enriched_pets)

        entity_job["status"] = "completed"
        entity_job["completedAt"] = datetime.utcnow().isoformat()
        entity_job["count"] = len(enriched_pets)
        logger.info(f"Fetched and processed {len(enriched_pets)} pets successfully")
    except Exception as e:
        entity_job["status"] = "failed"
        entity_job["error"] = str(e)
        logger.exception("Error in processing entity job")


@app.route("/pets/fetch", methods=["POST"])
async def fetch_pets():
    data = await request.get_json()
    status = data.get("status")
    pet_type = data.get("type")
    limit = data.get("limit", 10)

    if not isinstance(limit, int) or limit <= 0:
        limit = 10

    job_id = f"job-{datetime.utcnow().timestamp()}"

    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
    }

    # Fire and forget processing task
    asyncio.create_task(process_entity(entity_jobs[job_id], {"status": status, "type": pet_type, "limit": limit}))

    return jsonify({"message": "Pets data fetch started", "job_id": job_id}), 202


@app.route("/pets", methods=["GET"])
async def get_pets():
    # Return current cached pets data
    return jsonify(pets_data)


@app.route("/pets/customize-message", methods=["POST"])
async def customize_message():
    data = await request.get_json()
    pet_id = data.get("pet_id")
    message_template = data.get("message_template")

    if pet_id is None or not message_template:
        return jsonify({"error": "pet_id and message_template are required"}), 400

    # Find pet
    pet = next((p for p in pets_data if p["id"] == pet_id), None)
    if not pet:
        return jsonify({"error": f"Pet with id {pet_id} not found"}), 404

    # Replace placeholders in template
    # Support {name} placeholder for now
    try:
        updated_description = message_template.format(name=pet["name"])
    except Exception as e:
        logger.exception("Error formatting message template")
        return jsonify({"error": "Invalid message_template format"}), 400

    pet["description"] = updated_description

    return jsonify({"pet_id": pet_id, "updated_description": updated_description})


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
