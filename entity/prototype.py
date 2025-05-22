from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data models for request validation
@dataclass
class FetchRequest:
    status: Optional[str]
    type: Optional[str]
    limit: int

@dataclass
class CustomizeMessage:
    pet_id: int
    message_template: str

# In-memory cache for pets data and job statuses
pets_data: List[Dict] = []
entity_jobs: Dict[str, Dict] = {}

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

async def fetch_pets_from_petstore(status: Optional[str], pet_type: Optional[str], limit: int) -> List[Dict]:
    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
    params = {"status": status or "available,pending,sold"}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            pets = response.json()
    except Exception as e:
        logger.exception("Failed to fetch pets from Petstore API")
        raise
    if pet_type:
        pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == pet_type.lower()]
    return pets[:limit]

def enrich_pet_description(pet: Dict) -> str:
    name = pet.get("name", "Unnamed")
    pet_type = pet.get("category", {}).get("name", "pet").lower()
    status = pet.get("status", "unknown")
    description = f"{name} is a lovely {pet_type} currently {status}."
    if pet_type == "cat":
        description += " Loves naps and chasing yarn balls! 😸"
    elif pet_type == "dog":
        description += " Always ready for a walk and lots of belly rubs! 🐶"
    else:
        description += " A wonderful companion waiting for you!"
    return description

async def process_entity(entity_job: Dict, params: Dict):
    try:
        pets = await fetch_pets_from_petstore(params.get("status"), params.get("type"), params.get("limit", 10))
        enriched = []
        for pet in pets:
            enriched.append({
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name", "").lower(),
                "status": pet.get("status"),
                "description": enrich_pet_description(pet),
            })
        pets_data.clear()
        pets_data.extend(enriched)
        entity_job.update({
            "status": "completed",
            "completedAt": datetime.utcnow().isoformat(),
            "count": len(enriched),
        })
        logger.info(f"Processed {len(enriched)} pets")
    except Exception as e:
        entity_job["status"] = "failed"
        entity_job["error"] = str(e)
        logger.exception("Error in processing entity job")

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchRequest)  # workaround: validate_request must be last in POST due to quart-schema issue
async def fetch_pets(data: FetchRequest):
    job_id = f"job-{datetime.utcnow().timestamp()}"
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
    }
    asyncio.create_task(process_entity(entity_jobs[job_id], data.__dict__))
    return jsonify({"message": "Pets data fetch started", "job_id": job_id}), 202

@app.route("/pets", methods=["GET"])
async def get_pets():
    return jsonify(pets_data)

@app.route("/pets/customize-message", methods=["POST"])
@validate_request(CustomizeMessage)  # workaround: validate_request must be last in POST due to quart-schema issue
async def customize_message(data: CustomizeMessage):
    pet = next((p for p in pets_data if p["id"] == data.pet_id), None)
    if not pet:
        return jsonify({"error": f"Pet with id {data.pet_id} not found"}), 404
    try:
        updated = data.message_template.format(name=pet["name"])
    except Exception:
        return jsonify({"error": "Invalid message_template format"}), 400
    pet["description"] = updated
    return jsonify({"pet_id": data.pet_id, "updated_description": updated})

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)