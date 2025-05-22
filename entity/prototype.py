```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory async-safe cache for pets data (id -> pet data)
# Using asyncio.Lock to avoid race conditions
pets_cache: Dict[int, Dict[str, Any]] = {}
pets_lock = asyncio.Lock()

# External Petstore API base URL (public Swagger Petstore)
PETSTORE_API_BASE = "https://petstore.swagger.io/v2"


async def fetch_pets_from_petstore(
    pet_type: Optional[str] = None, status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fetch pets from external Petstore API filtered by type and/or status.
    Since Petstore API does not have direct 'type' filter, we simulate filtering.
    """
    url = f"{PETSTORE_API_BASE}/pet/findByStatus"
    params = {}
    if status:
        params["status"] = status
    else:
        params["status"] = "available"  # default to available to limit results

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            pets = resp.json()

            # Filter by type if specified (Petstore 'category' field holds type info)
            if pet_type:
                pet_type_lower = pet_type.lower()
                filtered = []
                for pet in pets:
                    category = pet.get("category")
                    if category and isinstance(category, dict):
                        cat_name = category.get("name", "").lower()
                        if pet_type_lower == "other":
                            # Include pets not cat or dog
                            if cat_name not in ("cat", "dog"):
                                filtered.append(pet)
                        elif cat_name == pet_type_lower:
                            filtered.append(pet)
                    else:
                        # If no category info, treat as 'other' for safety
                        if pet_type_lower == "other":
                            filtered.append(pet)
                pets = filtered

            return pets

        except Exception as e:
            logger.exception(f"Failed to fetch pets from Petstore API: {e}")
            return []


async def store_pets(pets: List[Dict[str, Any]]):
    """
    Store pets data into in-memory cache asynchronously.
    """
    async with pets_lock:
        for pet in pets:
            pet_id = pet.get("id")
            if pet_id:
                pets_cache[pet_id] = pet


async def find_pet_matches(
    preferred_type: str, age_min: int, age_max: int, status: str
) -> List[Dict[str, Any]]:
    """
    Find pet matches from stored pets based on criteria.
    Age is taken from 'tags' or ignored if unavailable (Petstore API has no age field).
    We'll simulate age by random or default value as Petstore API lacks age.
    """
    async with pets_lock:
        results = []
        for pet in pets_cache.values():
            # Filter by type
            category = pet.get("category")
            cat_name = category.get("name", "").lower() if category else ""
            pet_type = cat_name if cat_name else "other"
            if preferred_type.lower() != pet_type and preferred_type.lower() != "other":
                continue

            # Filter by status
            pet_status = pet.get("status", "available")
            if pet_status != status:
                continue

            # Simulate age extraction - TODO: Petstore API does not provide age, so mock with 3
            age = 3  # TODO: Replace with real age if available

            if age_min <= age <= age_max:
                pet_result = {
                    "id": pet.get("id"),
                    "name": pet.get("name"),
                    "type": pet_type,
                    "age": age,
                    "status": pet_status,
                }
                results.append(pet_result)

        return results


@app.route("/pets/fetch", methods=["POST"])
async def pets_fetch():
    try:
        data = await request.get_json(force=True)
        pet_type = data.get("type")
        status = data.get("status")

        pets = await fetch_pets_from_petstore(pet_type, status)
        await store_pets(pets)

        return jsonify(
            {
                "message": "Pets data fetched successfully",
                "fetchedCount": len(pets),
            }
        )

    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to fetch pets"}), 500


@app.route("/pets/match", methods=["POST"])
async def pets_match():
    try:
        data = await request.get_json(force=True)
        preferred_type = data.get("preferredType")
        age_range = data.get("ageRange", {})
        status = data.get("status")

        if not preferred_type or not age_range or "min" not in age_range or "max" not in age_range or not status:
            return (
                jsonify(
                    {
                        "error": "Missing required fields: preferredType, ageRange[min,max], status"
                    }
                ),
                400,
            )

        matches = await find_pet_matches(
            preferred_type, age_range["min"], age_range["max"], status
        )

        return jsonify({"matches": matches})

    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to find pet matches"}), 500


@app.route("/pets", methods=["GET"])
async def pets_list():
    try:
        async with pets_lock:
            pets_list = list(pets_cache.values())
        return jsonify(pets_list)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pets"}), 500


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def pet_details(pet_id: int):
    try:
        async with pets_lock:
            pet = pets_cache.get(pet_id)
        if not pet:
            return jsonify({"error": "Pet not found"}), 404

        # Add a description field as per functional req (mocked)
        pet_detail = pet.copy()
        pet_detail["description"] = pet_detail.get(
            "description", "Playful pet who loves attention."
        )  # TODO: No real desc in Petstore API, so mocked

        return jsonify(pet_detail)

    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pet details"}), 500


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
