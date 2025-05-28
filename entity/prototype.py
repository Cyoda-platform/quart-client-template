import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data models for request validation
@dataclass
class FetchPetsRequest:
    status: Optional[str]  # available|pending|sold
    tags: Optional[List[str]]

@dataclass
class AdoptPetRequest:
    petId: int
    adopterName: str
    contact: str

# In-memory async-safe cache for pets and adoptions
class AsyncCache:
    def __init__(self):
        self._pets: List[Dict] = []
        self._adoptions: List[Dict] = []
        self._lock = asyncio.Lock()

    async def update_pets(self, pets: List[Dict]):
        async with self._lock:
            self._pets = pets

    async def get_pets(self) -> List[Dict]:
        async with self._lock:
            return list(self._pets)

    async def add_adoption(self, adoption: Dict):
        async with self._lock:
            self._adoptions.append(adoption)

    async def get_adoptions(self) -> List[Dict]:
        async with self._lock:
            return list(self._adoptions)

cache = AsyncCache()
PETSTORE_API_BASE = "https://petstore3.swagger.io/api/v3"

def filter_pets(pets: List[Dict], status: Optional[str], tags: Optional[List[str]]) -> List[Dict]:
    filtered = pets
    if status:
        filtered = [p for p in filtered if p.get("status") == status]
    if tags:
        filtered = [p for p in filtered if "tags" in p and any(tag["name"] in tags for tag in p["tags"])]
    return filtered

def process_petstore_pets(raw_pets: List[Dict]) -> List[Dict]:
    processed = []
    for pet in raw_pets:
        processed.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "status": pet.get("status"),
            "category": pet.get("category", {}).get("name") if pet.get("category") else None,
            "tags": [tag.get("name") for tag in pet.get("tags", [])] if pet.get("tags") else [],
        })
    return processed

async def process_fetch_pets_job(status: Optional[str], tags: Optional[List[str]]):
    async with httpx.AsyncClient() as client:
        try:
            url = f"{PETSTORE_API_BASE}/pet/findByStatus"
            params = {"status": status or "available,pending,sold"}
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            raw_pets = response.json()
            filtered_pets = filter_pets(raw_pets, None, tags)
            processed = process_petstore_pets(filtered_pets)
            await cache.update_pets(processed)
            logger.info(f"Fetched and processed {len(processed)} pets")
        except Exception as e:
            logger.exception(e)

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)  # validation last for POST requests (workaround for quart-schema bug)
async def fetch_pets(data: FetchPetsRequest):
    requested_at = datetime.utcnow().isoformat()
    logger.info(f"Fetch request at {requested_at} with status={data.status} tags={data.tags}")
    asyncio.create_task(process_fetch_pets_job(data.status, data.tags))
    return jsonify({"message": "Pets fetch job started"}), 202

@app.route("/pets", methods=["GET"])
async def get_pets():
    pets = await cache.get_pets()
    return jsonify(pets)

@app.route("/pets/adopt", methods=["POST"])
@validate_request(AdoptPetRequest)  # validation last for POST requests (workaround for quart-schema bug)
async def adopt_pet(data: AdoptPetRequest):
    adoption_request = {
        "requestId": int(datetime.utcnow().timestamp() * 1000),
        "petId": data.petId,
        "adopterName": data.adopterName,
        "contact": data.contact,
        "status": "pending",
        "requestedAt": datetime.utcnow().isoformat(),
    }
    await cache.add_adoption(adoption_request)
    logger.info(f"New adoption request: {adoption_request}")
    return jsonify({"message": "Adoption request submitted", "requestId": adoption_request["requestId"]})

@app.route("/adoptions", methods=["GET"])
async def get_adoptions():
    adoptions = await cache.get_adoptions()
    return jsonify(adoptions)

if __name__ == '__main__':
    import sys
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        level=logging.INFO,
        stream=sys.stdout,
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)