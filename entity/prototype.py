import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# request schemas
@dataclass
class PetFetchRequest:
    filter: dict  # TODO: refine type once nested schemas are supported

@dataclass
class FunFactRequest:
    type: Optional[str] = None

# In-memory cache for pets data and fun facts
pets_cache: List[dict] = []
fun_facts_cache: List[str] = [
    "Cats sleep for 70% of their lives.",
    "Dogs have a sense of time and can miss you.",
    "Rabbits can see behind them without turning their heads.",
    "Guinea pigs communicate with purrs and squeaks.",
    "Parrots can live for over 80 years."
]

PETSTORE_API_BASE = "https://petstore3.swagger.io/api/v3"
pets_cache_lock = asyncio.Lock()

async def fetch_pets_from_external_api(status: Optional[str], pet_type: Optional[str]) -> List[dict]:
    async with httpx.AsyncClient() as client:
        try:
            params = {}
            if status:
                params["status"] = status
            resp = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params=params)
            resp.raise_for_status()
            pets = resp.json()
            if pet_type:
                pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == pet_type.lower()]
            return pets
        except Exception as e:
            logger.exception(f"Failed to fetch pets: {e}")
            return []

def enrich_pet_with_fun_fact(pet: dict) -> dict:
    import random
    pet_copy = pet.copy()
    pet_copy["funFact"] = random.choice(fun_facts_cache)
    return pet_copy

async def process_entity(entity_job: dict, data: dict):
    try:
        pets = await fetch_pets_from_external_api(data.get("status"), data.get("type"))
        pets_enriched = [enrich_pet_with_fun_fact(p) for p in pets]
        async with pets_cache_lock:
            pets_cache.clear()
            pets_cache.extend(pets_enriched)
        entity_job["status"] = "completed"
        entity_job["completedAt"] = datetime.utcnow().isoformat()
        entity_job["count"] = len(pets_enriched)
        logger.info(f"Processed {len(pets_enriched)} pets successfully.")
    except Exception as e:
        entity_job["status"] = "failed"
        logger.exception(f"Error processing entity: {e}")

@app.route("/pets/fetch", methods=["POST"])
@validate_request(PetFetchRequest)  # workaround: validation last for POST
async def fetch_pets(data: PetFetchRequest):
    filter_data = data.filter or {}
    status = filter_data.get("status")
    pet_type = filter_data.get("type")
    job_id = datetime.utcnow().isoformat()
    entity_job = {"status": "processing", "requestedAt": job_id}
    asyncio.create_task(process_entity(entity_job, filter_data))
    return jsonify({"message": "Pets fetch started", "requestedAt": job_id})

@app.route("/pets", methods=["GET"])
async def get_pets():
    async with pets_cache_lock:
        pets = list(pets_cache)
    return jsonify(pets)

@app.route("/pets/funfact", methods=["POST"])
@validate_request(FunFactRequest)  # workaround: validation last for POST
async def get_fun_fact(data: FunFactRequest):
    import random
    fun_fact = random.choice(fun_facts_cache)
    return jsonify({"funFact": fun_fact})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)