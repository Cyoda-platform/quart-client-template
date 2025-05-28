```python
import asyncio
import logging
import random
from datetime import datetime
from typing import List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory async-safe cache using asyncio.Lock
class PetStoreCache:
    def __init__(self):
        self._pets = []
        self._lock = asyncio.Lock()

    async def set_pets(self, pets: List[dict]):
        async with self._lock:
            self._pets = pets

    async def get_pets(self, pet_type: Optional[str] = None, status: Optional[str] = None) -> List[dict]:
        async with self._lock:
            pets = self._pets
            if pet_type:
                pets = [p for p in pets if p.get("type") == pet_type]
            if status:
                pets = [p for p in pets if p.get("status") == status]
            return pets

    async def get_pet_by_id(self, pet_id: int) -> Optional[dict]:
        async with self._lock:
            for pet in self._pets:
                if pet.get("id") == pet_id:
                    return pet
            return None

    async def get_random_pet(self, pet_type: Optional[str] = None) -> Optional[dict]:
        pets = await self.get_pets(pet_type=pet_type)
        if pets:
            return random.choice(pets)
        return None


cache = PetStoreCache()

# Constants
PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

# Helper to normalize pet data from Petstore API response (which is a Swagger Pet)
def normalize_pet_data(raw_pet: dict) -> dict:
    # Petstore API schema reference:
    # https://petstore.swagger.io/v2/swagger.json
    # Core fields: id, name, photoUrls, status, tags, category (type is category.name)
    pet_type = raw_pet.get("category", {}).get("name") if raw_pet.get("category") else None
    tags = [t["name"] for t in raw_pet.get("tags", [])] if raw_pet.get("tags") else []
    return {
        "id": raw_pet.get("id"),
        "name": raw_pet.get("name"),
        "type": pet_type,
        "status": raw_pet.get("status"),
        "tags": tags,
        "photoUrls": raw_pet.get("photoUrls", []),
    }


async def fetch_pets_from_petstore(pet_type: Optional[str], status: Optional[str]) -> List[dict]:
    """Fetch pets from Petstore API filtered by status. Petstore API doesn't support filtering by category/type on server side, so we filter client-side."""
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            # Petstore API /pet/findByStatus supports status filtering
            if status:
                resp = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": status})
                resp.raise_for_status()
                pets_raw = resp.json()
            else:
                # No direct way to get all pets if no status filter, fallback to available + pending + sold
                pets_raw = []
                for s in ["available", "pending", "sold"]:
                    resp = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": s})
                    resp.raise_for_status()
                    pets_raw.extend(resp.json())
            # Normalize and optionally filter by type (category.name)
            pets = [normalize_pet_data(p) for p in pets_raw]
            if pet_type:
                pets = [p for p in pets if p.get("type") == pet_type]
            return pets
        except Exception as e:
            logger.exception(e)
            return []


async def process_pet_fetch_job(pet_type: Optional[str], status: Optional[str]):
    logger.info(f"Started pet fetch job with type={pet_type} status={status}")
    pets = await fetch_pets_from_petstore(pet_type=pet_type, status=status)
    await cache.set_pets(pets)
    logger.info(f"Fetched and stored {len(pets)} pets")


@app.route("/pets/fetch", methods=["POST"])
async def pets_fetch():
    data = await request.get_json(force=True)
    pet_type = data.get("type")
    status = data.get("status")
    requested_at = datetime.utcnow().isoformat()

    # Fire and forget the fetch + store task
    asyncio.create_task(process_pet_fetch_job(pet_type, status))

    return jsonify({
        "message": "Pets fetch job started",
        "requestedAt": requested_at
    })


@app.route("/pets", methods=["GET"])
async def pets_list():
    pet_type = request.args.get("type")
    status = request.args.get("status")
    pets = await cache.get_pets(pet_type=pet_type, status=status)
    return jsonify(pets)


@app.route("/pets/random", methods=["POST"])
async def pets_random():
    data = await request.get_json(silent=True) or {}
    pet_type = data.get("type")
    pet = await cache.get_random_pet(pet_type=pet_type)
    if pet:
        return jsonify(pet)
    else:
        return jsonify({"message": "No pet found matching criteria"}), 404


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def pet_detail(pet_id: int):
    pet = await cache.get_pet_by_id(pet_id)
    if pet:
        return jsonify(pet)
    else:
        return jsonify({"message": "Pet not found"}), 404


if __name__ == '__main__':
    import sys
    import logging
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
