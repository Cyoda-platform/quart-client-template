```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory async-safe cache using asyncio.Lock
class AsyncCache:
    def __init__(self):
        self._pets: Optional[Dict[str, Any]] = None
        self._pets_lock = asyncio.Lock()
        self._stats: Optional[Dict[str, Any]] = None
        self._stats_lock = asyncio.Lock()

    async def set_pets(self, data: Dict[str, Any]):
        async with self._pets_lock:
            self._pets = data

    async def get_pets(self) -> Optional[Dict[str, Any]]:
        async with self._pets_lock:
            return self._pets

    async def set_stats(self, data: Dict[str, Any]):
        async with self._stats_lock:
            self._stats = data

    async def get_stats(self) -> Optional[Dict[str, Any]]:
        async with self._stats_lock:
            return self._stats


cache = AsyncCache()

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

# Fun facts by species (simple static map for prototype)
FUN_FACTS = {
    "dog": "Dogs have three eyelids!",
    "cat": "Cats have five toes on front paws but four on back paws.",
    "bird": "Some birds can mimic human speech.",
    # TODO: Expand fun facts or fetch dynamically if desired
}

async def fetch_pets_from_petstore(species: Optional[str], status: Optional[str]) -> list:
    """
    Fetch pets from the Petstore API filtered by status.
    Petstore API supports GET /pet/findByStatus (status parameter required).
    Species filtering is not supported by API, so we will filter client-side.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Petstore API requires status param (comma separated list)
            # If status is None, default to all statuses per Petstore docs
            status_param = status if status else "available,pending,sold"
            response = await client.get(
                f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": status_param}
            )
            response.raise_for_status()
            pets = response.json()
            # Filter by species client-side if provided
            if species:
                species_lower = species.lower()
                filtered = [
                    pet for pet in pets
                    if pet.get("category", {}).get("name", "").lower() == species_lower
                ]
                return filtered
            else:
                return pets
    except Exception as e:
        logger.exception(f"Error fetching pets from Petstore: {e}")
        return []

def enrich_pets_with_fun_facts(pets: list) -> list:
    enriched = []
    for pet in pets:
        species = pet.get("category", {}).get("name", "").lower()
        fun_fact = FUN_FACTS.get(species, "Pets bring joy to our lives!")
        enriched.append(
            {
                "id": pet.get("id"),
                "name": pet.get("name"),
                "species": species,
                "status": pet.get("status"),
                "fun_fact": fun_fact,
            }
        )
    return enriched

def calculate_stats(pets: list, species_filter: Optional[str]) -> Dict[str, Any]:
    filtered = pets
    if species_filter:
        sf = species_filter.lower()
        filtered = [p for p in pets if p.get("species") == sf]
    total = len(filtered)
    status_count = {"available": 0, "pending": 0, "sold": 0}
    for pet in filtered:
        st = pet.get("status")
        if st in status_count:
            status_count[st] += 1
    return {
        "species": species_filter if species_filter else "all",
        "total_pets": total,
        "available": status_count["available"],
        "pending": status_count["pending"],
        "sold": status_count["sold"],
    }

async def process_fetch_pets_job(data: Dict[str, Any]):
    species = data.get("species")
    status = data.get("status")
    pets_raw = await fetch_pets_from_petstore(species, status)
    pets_enriched = enrich_pets_with_fun_facts(pets_raw)
    # Cache the enriched pets for GET /pets
    await cache.set_pets({"pets": pets_enriched})

async def process_fetch_stats_job(data: Dict[str, Any]):
    species = data.get("species")
    # For stats, fetch all statuses for given species
    pets_raw = await fetch_pets_from_petstore(species, None)
    pets_enriched = enrich_pets_with_fun_facts(pets_raw)
    stats = calculate_stats(pets_enriched, species)
    # Cache stats for GET /pets/stats
    await cache.set_stats(stats)

@app.route("/pets/fetch", methods=["POST"])
async def fetch_pets():
    try:
        data = await request.get_json(force=True)
        # Fire and forget processing task
        asyncio.create_task(process_fetch_pets_job(data))
        return jsonify({"status": "processing", "requestedAt": datetime.utcnow().isoformat()})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to start pets fetch job"}), 500

@app.route("/pets", methods=["GET"])
async def get_pets():
    pets = await cache.get_pets()
    if pets is None:
        return jsonify({"error": "No pets data cached yet"}), 404
    return jsonify(pets)

@app.route("/pets/stats", methods=["POST"])
async def fetch_stats():
    try:
        data = await request.get_json(force=True)
        asyncio.create_task(process_fetch_stats_job(data))
        return jsonify({"status": "processing", "requestedAt": datetime.utcnow().isoformat()})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to start stats fetch job"}), 500

@app.route("/pets/stats", methods=["GET"])
async def get_stats():
    stats = await cache.get_stats()
    if stats is None:
        return jsonify({"error": "No stats data cached yet"}), 404
    return jsonify(stats)


if __name__ == '__main__':
    import sys
    import logging

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
