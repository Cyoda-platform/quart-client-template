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

# Local in-memory cache for pets and last filtered result (async-safe pattern: using asyncio.Lock)
pets_cache: List[Dict] = []
filtered_cache: List[Dict] = []
pets_lock = asyncio.Lock()
filtered_lock = asyncio.Lock()

# External Petstore API base URL
PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

# Utility to map Petstore API pet to internal pet model with age mocked
def map_petstore_pet(pet: Dict) -> Dict:
    # TODO: Petstore API pets do not have age; we mock age here for demo/testing
    import random

    return {
        "id": pet.get("id"),
        "name": pet.get("name"),
        "type": pet.get("category", {}).get("name", "unknown") if pet.get("category") else "unknown",
        "status": pet.get("status", "available"),
        "age": random.randint(1, 10),  # TODO: Replace with real age if available
    }


@app.route("/pets/fetch", methods=["POST"])
async def fetch_pets():
    """
    Fetch pet data from external Petstore API by status and optional type.
    Cache/store internally.
    """
    data = await request.get_json()
    status = data.get("status")
    pet_type = data.get("type")

    if status not in {"available", "pending", "sold"}:
        return jsonify({"error": "Invalid or missing status"}), 400

    params = {"status": status}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params=params)
            response.raise_for_status()
            pets_data = response.json()
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to fetch data from external Petstore API"}), 502

    # Filter by type if requested
    if pet_type:
        pets_data = [p for p in pets_data if (p.get("category", {}).get("name") or "").lower() == pet_type.lower()]

    # Map and cache pets
    mapped_pets = [map_petstore_pet(p) for p in pets_data]

    async with pets_lock:
        pets_cache.clear()
        pets_cache.extend(mapped_pets)

    async with filtered_lock:
        filtered_cache.clear()
        filtered_cache.extend(mapped_pets)

    return jsonify({"message": "Pets data fetched and stored", "count": len(mapped_pets)})


@app.route("/pets/filter", methods=["POST"])
async def filter_pets():
    """
    Filter stored pets by provided criteria and cache filtered result.
    """
    data = await request.get_json()
    pet_type: Optional[str] = data.get("type")
    status: Optional[str] = data.get("status")
    min_age: Optional[int] = data.get("min_age")
    max_age: Optional[int] = data.get("max_age")

    async with pets_lock:
        pets_list = pets_cache.copy()

    def pet_matches(pet: Dict) -> bool:
        if pet_type and pet["type"].lower() != pet_type.lower():
            return False
        if status and pet["status"].lower() != status.lower():
            return False
        if min_age is not None and pet["age"] < min_age:
            return False
        if max_age is not None and pet["age"] > max_age:
            return False
        return True

    filtered = [p for p in pets_list if pet_matches(p)]

    async with filtered_lock:
        filtered_cache.clear()
        filtered_cache.extend(filtered)

    return jsonify({"pets": filtered})


@app.route("/pets", methods=["GET"])
async def get_pets():
    """
    Retrieve last filtered or fetched pet list.
    """
    async with filtered_lock:
        result = filtered_cache.copy()
    return jsonify({"pets": result})


@app.route("/pets/adopt", methods=["POST"])
async def adopt_pet():
    """
    Process pet adoption request. This demo mocks adoption call.
    """
    data = await request.get_json()
    pet_id = data.get("pet_id")
    adopter_name = data.get("adopter_name")
    adopter_contact = data.get("adopter_contact")

    if not all([pet_id, adopter_name, adopter_contact]):
        return jsonify({"error": "pet_id, adopter_name, and adopter_contact are required"}), 400

    # Check if pet exists in cache
    async with pets_lock:
        pet = next((p for p in pets_cache if p["id"] == pet_id), None)

    if not pet:
        return jsonify({"error": "Pet not found"}), 404

    # TODO: In real implementation, call external API to update pet status/adoption
    # Simulate async adoption processing
    async def process_adoption():
        await asyncio.sleep(1)  # simulate delay
        # For prototype, update pet status locally
        async with pets_lock:
            for p in pets_cache:
                if p["id"] == pet_id:
                    p["status"] = "adopted"
        async with filtered_lock:
            for p in filtered_cache:
                if p["id"] == pet_id:
                    p["status"] = "adopted"

    # Fire and forget adoption processing
    asyncio.create_task(process_adoption())

    logger.info(f"Adoption requested for pet_id={pet_id} by {adopter_name}")

    return jsonify({"message": "Adoption request processed", "pet_id": pet_id, "status": "pending"})


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
