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

# In-memory async-safe cache for last queried pets results (per "session")
# In real app, consider proper async-safe cache or DB.
class Cache:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._data: Optional[Dict[str, Any]] = None

    async def set(self, data: Dict[str, Any]):
        async with self._lock:
            self._data = data

    async def get(self) -> Optional[Dict[str, Any]]:
        async with self._lock:
            return self._data


cache = Cache()

PETSTORE_BASE = "https://petstore.swagger.io/v2"

# Helper to fetch pets by filters from Petstore API
async def fetch_pets(filters: Dict[str, Any]) -> Dict[str, Any]:
    # Petstore API supports: /pet/findByStatus or /pet/findByTags
    # We'll map filters accordingly.
    # If type or name filters exist, we do client-side filtering (Petstore API has limited filter support).
    # The only official filtered endpoint is by status.
    # TODO: If API expands, adjust filtering here.

    status = filters.get("status")
    pet_type = filters.get("type")
    name_filter = filters.get("name")

    pets = []

    async with httpx.AsyncClient() as client:
        try:
            if status:
                # Petstore supports findByStatus endpoint
                r = await client.get(f"{PETSTORE_BASE}/pet/findByStatus", params={"status": status})
                r.raise_for_status()
                pets = r.json()
            else:
                # No status filter: fetch all available statuses (available, pending, sold)
                pets = []
                for st in ["available", "pending", "sold"]:
                    r = await client.get(f"{PETSTORE_BASE}/pet/findByStatus", params={"status": st})
                    r.raise_for_status()
                    pets.extend(r.json())
        except Exception as e:
            logger.exception("Error fetching pets from Petstore API")
            raise

    # Filter by type and name client-side
    def match(pet: Dict[str, Any]) -> bool:
        if pet_type and pet.get("category", {}).get("name", "").lower() != pet_type.lower():
            return False
        if name_filter and name_filter.lower() not in pet.get("name", "").lower():
            return False
        return True

    filtered = [pet for pet in pets if match(pet)]

    # Normalize output to required fields
    result = []
    for pet in filtered:
        result.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name"),
            "status": pet.get("status"),
            "photoUrls": pet.get("photoUrls", []),
        })
    return {"pets": result}


# Helper to fetch pet details by ID
async def fetch_pet_details(pet_id: int) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{PETSTORE_BASE}/pet/{pet_id}")
            r.raise_for_status()
            pet = r.json()
        except httpx.HTTPStatusError as e:
            logger.exception(f"Pet with ID {pet_id} not found or other HTTP error")
            return {"error": f"Pet with ID {pet_id} not found."}
        except Exception as e:
            logger.exception("Error fetching pet details from Petstore API")
            raise

    # Normalize output with additional fields
    return {
        "id": pet.get("id"),
        "name": pet.get("name"),
        "type": pet.get("category", {}).get("name"),
        "status": pet.get("status"),
        "photoUrls": pet.get("photoUrls", []),
        "tags": [tag.get("name") for tag in pet.get("tags", []) if "name" in tag],
        "description": pet.get("description") or "",
    }


# POST /pets/query - query pets with filters and business logic
@app.route("/pets/query", methods=["POST"])
async def pets_query():
    try:
        data = await request.get_json(force=True)
        filters = data.get("filters", {}) if data else {}

        # Fire and forget pattern: store job status (mocked here as immediate processing)
        requested_at = datetime.utcnow().isoformat()
        job_id = f"query_{requested_at}"

        # Process query immediately for prototype
        pets_data = await fetch_pets(filters)

        # Cache last query results for GET /pets
        await cache.set(pets_data)

        return jsonify(pets_data)
    except Exception as e:
        logger.exception("Failed processing /pets/query")
        return jsonify({"error": "Failed to process pets query"}), 500


# GET /pets - retrieve last queried pets results stored in app
@app.route("/pets", methods=["GET"])
async def get_last_pets():
    try:
        pets_data = await cache.get()
        if not pets_data:
            return jsonify({"pets": []})
        return jsonify(pets_data)
    except Exception as e:
        logger.exception("Failed processing GET /pets")
        return jsonify({"error": "Failed to retrieve cached pets data"}), 500


# POST /pets/details - fetch pet details by ID
@app.route("/pets/details", methods=["POST"])
async def pets_details():
    try:
        data = await request.get_json(force=True)
        pet_id = data.get("petId")
        if not pet_id or not isinstance(pet_id, int):
            return jsonify({"error": "Invalid or missing petId"}), 400

        pet_details = await fetch_pet_details(pet_id)
        if "error" in pet_details:
            return jsonify(pet_details), 404

        return jsonify(pet_details)
    except Exception as e:
        logger.exception("Failed processing /pets/details")
        return jsonify({"error": "Failed to fetch pet details"}), 500


if __name__ == '__main__':
    import sys
    import logging.config

    # Simple logging config for console output
    logging.basicConfig(
        stream=sys.stdout,
        format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        level=logging.INFO,
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
