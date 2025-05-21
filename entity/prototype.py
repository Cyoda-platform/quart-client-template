import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class Filter:
    type: str = "all"

@dataclass
class FunFeatures:
    includeFacts: bool = False
    includeImages: bool = False

@dataclass
class FetchPetsRequest:
    filter: Filter
    funFeatures: FunFeatures

# In-memory async-safe "cache" for processed pets and facts.
# Use asyncio.Lock for concurrency safety.
class AppState:
    def __init__(self):
        self._pets: List[Dict] = []
        self._fun_facts: List[str] = []
        self._lock = asyncio.Lock()

    async def update_pets(self, pets: List[Dict]):
        async with self._lock:
            self._pets = pets

    async def get_pets(self) -> List[Dict]:
        async with self._lock:
            return list(self._pets)

    async def update_facts(self, facts: List[str]):
        async with self._lock:
            self._fun_facts = facts

    async def get_random_fact(self) -> Optional[str]:
        import random
        async with self._lock:
            if not self._fun_facts:
                return None
            return random.choice(self._fun_facts)

app_state = AppState()

PETSTORE_API_URL = "https://petstore.swagger.io/v2/pet/findByStatus?status=available"
DEFAULT_FUN_FACTS = [
    "A group of cats is called a clowder.",
    "Cats sleep for 70% of their lives.",
    "Dogs have about 1,700 taste buds.",
    "Cats can make over 100 different sounds.",
    "Dogs' sense of smell is about 40 times better than humans'.",
]

def enrich_pets(pets: List[Dict], include_facts: bool, include_images: bool) -> List[Dict]:
    from random import choice
    enriched = []
    for pet in pets:
        pet_copy = dict(pet)
        if include_facts:
            pet_copy["funFact"] = choice(DEFAULT_FUN_FACTS)
        if include_images:
            photos = pet_copy.get("photoUrls", [])
            pet_copy["imageUrl"] = photos[0] if photos else None
        enriched.append(pet_copy)
    return enriched

async def fetch_petstore_data() -> List[Dict]:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(PETSTORE_API_URL, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
            if not isinstance(pets, list):
                logger.warning("Petstore API returned unexpected data format")
                return []
            return pets
        except Exception as e:
            logger.exception(f"Error fetching data from Petstore API: {e}")
            return []

async def filter_pets_by_type(pets: List[Dict], pet_type: str) -> List[Dict]:
    if pet_type.lower() == "all":
        return pets
    filtered = []
    for pet in pets:
        category = pet.get("category")
        if category and isinstance(category, dict):
            name = category.get("name", "").lower()
            if name == pet_type.lower():
                filtered.append(pet)
    return filtered

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)  # workaround: validate_request defect, POST requires validation last
async def fetch_and_process_pets(data: FetchPetsRequest):
    pet_type = data.filter.type
    include_facts = data.funFeatures.includeFacts
    include_images = data.funFeatures.includeImages

    requested_at = datetime.utcnow().isoformat()
    job_id = requested_at
    entity_job = {job_id: {"status": "processing", "requestedAt": requested_at}}

    async def process_entity(entity_job: Dict, job_id: str):
        logger.info(f"Started processing job {job_id}")
        try:
            pets_raw = await fetch_petstore_data()
            pets_filtered = await filter_pets_by_type(pets_raw, pet_type)
            pets_enriched = enrich_pets(pets_filtered, include_facts, include_images)
            await app_state.update_pets(pets_enriched)
            if include_facts:
                facts = list({p.get("funFact") for p in pets_enriched if p.get("funFact")})
                if not facts:
                    facts = DEFAULT_FUN_FACTS
                await app_state.update_facts(facts)
            else:
                await app_state.update_facts([])
            entity_job[job_id]["status"] = "completed"
            logger.info(f"Completed processing job {job_id} with {len(pets_enriched)} pets")
        except Exception as e:
            entity_job[job_id]["status"] = "error"
            logger.exception(f"Error processing job {job_id}: {e}")

    asyncio.create_task(process_entity(entity_job, job_id))
    return jsonify({
        "message": "Pets data fetching and processing started",
        "requestedAt": requested_at,
        "status": entity_job[job_id]["status"],
    })

@app.route("/pets", methods=["GET"])
async def get_processed_pets():
    pets = await app_state.get_pets()
    def map_pet(pet: Dict) -> Dict:
        category = pet.get("category", {})
        return {
            "id": str(pet.get("id", "")),
            "name": pet.get("name", ""),
            "type": category.get("name", "") if isinstance(category, dict) else "",
            "age": pet.get("age", None),  # TODO: Placeholder - Petstore API has no age
            "funFact": pet.get("funFact"),
            "imageUrl": pet.get("imageUrl"),
        }
    pets_mapped = [map_pet(p) for p in pets]
    return jsonify({"pets": pets_mapped})

@app.route("/pets/funfact", methods=["GET"])
async def get_random_fun_fact():
    fact = await app_state.get_random_fact()
    if not fact:
        fact = "Did you know? Cats have five toes on their front paws, but only four on the back."
    return jsonify({"funFact": fact})

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        stream=sys.stdout,
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)