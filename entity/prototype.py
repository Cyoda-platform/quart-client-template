from dataclasses import dataclass
from typing import Optional, List, Dict
import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data classes for request validation
@dataclass
class PetFetchFilter:
    status: Optional[str] = None
    type: Optional[str] = None

@dataclass
class PetsFetchRequest:
    filter: PetFetchFilter
    enhance: Optional[bool] = False

@dataclass
class PetsGetQuery:
    job_id: str

@dataclass
class PetsFilterFilter:
    type: Optional[str] = None
    status: Optional[str] = None
    personality: Optional[str] = None

@dataclass
class PetsFilterRequest:
    job_id: str
    filter: PetsFilterFilter

# In-memory store for jobs
entity_job: Dict[str, Dict] = {}

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

async def fetch_pets_from_petstore(status: Optional[str], pet_type: Optional[str]) -> List[Dict]:
    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
    params = {"status": status or "available"}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(f"Error fetching pets: {e}")
            return []
    if pet_type:
        pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == pet_type.lower()]
    return pets

def add_personality_traits(pets: List[Dict]) -> List[Dict]:
    personality_map = {
        "cat": ["playful and curious", "lazy and cuddly", "mischievous and clever", "independent and mysterious"],
        "dog": ["friendly and loyal", "energetic and goofy", "calm and protective", "eager and attentive"],
    }
    import random
    enhanced = []
    for pet in pets:
        copy = pet.copy()
        pet_type = copy.get("category", {}).get("name", "").lower()
        copy["personality"] = random.choice(personality_map.get(pet_type, ["adorable and unique"]))
        enhanced.append(copy)
    return enhanced

async def process_entity(job_id: str, filt: PetFetchFilter, enhance: bool):
    try:
        pets = await fetch_pets_from_petstore(filt.status, filt.type)
        logger.info(f"Job {job_id}: fetched {len(pets)} pets")
        if enhance:
            pets = add_personality_traits(pets)
            logger.info(f"Job {job_id}: enhanced pets")
        entity_job[job_id]["pets"] = pets
        entity_job[job_id]["status"] = "done"
    except Exception as e:
        logger.exception(f"Error in job {job_id}: {e}")
        entity_job[job_id]["status"] = "error"
        entity_job[job_id]["pets"] = []

@app.route("/pets/fetch", methods=["POST"])
# Issue workaround: for POST, place validate_request decorator after route decorator
@validate_request(PetsFetchRequest)
async def pets_fetch(data: PetsFetchRequest):
    filt = data.filter
    enhance = data.enhance or False
    job_id = datetime.utcnow().isoformat() + "-" + str(id(data))
    entity_job[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat(), "pets": []}
    asyncio.create_task(process_entity(job_id, filt, enhance))
    return jsonify({"job_id": job_id, "status": "processing"}), 202

# Issue workaround: for GET, place validate_querystring decorator before route decorator
@validate_querystring(PetsGetQuery)
@app.route("/pets", methods=["GET"])
async def pets_get():
    job_id = request.args.get("job_id")
    if not job_id or job_id not in entity_job:
        return jsonify({"error": "job_id missing or not found"}), 400
    job = entity_job[job_id]
    return jsonify({"status": job["status"], "pets": job.get("pets", [])})

@app.route("/pets/filter", methods=["POST"])
# Issue workaround: for POST, place validate_request decorator after route decorator
@validate_request(PetsFilterRequest)
async def pets_filter(data: PetsFilterRequest):
    job_id = data.job_id
    if job_id not in entity_job:
        return jsonify({"error": "job_id missing or not found"}), 400
    if entity_job[job_id]["status"] != "done":
        return jsonify({"error": "pets data not ready"}), 400
    pets = entity_job[job_id]["pets"]
    f = data.filter
    def match(p):
        if f.type and p.get("category", {}).get("name", "").lower() != f.type.lower():
            return False
        if f.status and p.get("status", "").lower() != f.status.lower():
            return False
        if f.personality and f.personality.lower() not in p.get("personality", "").lower():
            return False
        return True
    filtered = [p for p in pets if match(p)]
    return jsonify({"pets": filtered})

if __name__ == "__main__":
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)