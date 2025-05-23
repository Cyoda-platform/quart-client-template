```python
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory "local store" for pets
# Structure: pet_id (str) -> pet_data (dict)
_local_pet_store: Dict[str, Dict] = {}

# Petstore API base URL (OpenAPI Petstore)
PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"

# Helper to generate new pet IDs locally (UUID4)
def generate_pet_id() -> str:
    return str(uuid.uuid4())

# ===================
# Business Logic Tasks
# ===================

async def fetch_pets_from_petstore(
    type_: Optional[str], status: Optional[str], name: Optional[str]
) -> List[Dict]:
    """
    Query Petstore API to search pets by status.
    Petstore API supports filtering by status only on /pet/findByStatus.
    We will combine results client side for type and name filtering.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        pets = []
        try:
            # Petstore API supports filtering by status (comma separated)
            if status:
                r = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": status})
            else:
                # If no status specified, fetch all statuses sequentially (TODO: Petstore has limited endpoints)
                pets_accum = []
                for st in ["available", "pending", "sold"]:
                    r = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": st})
                    if r.status_code == 200:
                        pets_accum.extend(r.json())
                return pets_accum

            r.raise_for_status()
            pets = r.json()

            # Filter by type and name client side (type is pet.category.name in Petstore API)
            def pet_matches(pet):
                if type_:
                    pet_type = pet.get("category", {}).get("name", "")
                    if pet_type.lower() != type_.lower():
                        return False
                if name:
                    pet_name = pet.get("name", "")
                    if name.lower() not in pet_name.lower():
                        return False
                return True

            pets = [p for p in pets if pet_matches(p)]
            return pets
        except Exception as e:
            logger.exception(f"Error fetching pets from Petstore API: {e}")
            return []

# =======================
# API Endpoints (Handlers)
# =======================

@app.route("/pets/search", methods=["POST"])
async def search_pets():
    """
    Search pets by criteria using Petstore API (external call).
    Request body example:
    {
        "type": "string",    # optional
        "status": "string",  # optional
        "name": "string"     # optional
    }
    """
    data = await request.get_json(force=True)
    type_ = data.get("type")
    status = data.get("status")
    name = data.get("name")

    pets = await fetch_pets_from_petstore(type_, status, name)

    # Map Petstore pet format to simplified response format
    def map_pet(pet):
        return {
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name", ""),
            "status": pet.get("status", ""),
            "photoUrls": pet.get("photoUrls", []),
        }

    mapped_pets = [map_pet(p) for p in pets]
    return jsonify({"pets": mapped_pets})


@app.route("/pets", methods=["POST"])
async def add_pet():
    """
    Add a new pet to local store.
    Request body:
    {
        "name": "string",
        "type": "string",
        "status": "string",
        "photoUrls": ["string"]
    }
    """
    data = await request.get_json(force=True)
    # Minimal validation TODO: improve as needed
    name = data.get("name")
    type_ = data.get("type")
    status = data.get("status")
    photo_urls = data.get("photoUrls", [])

    if not (name and type_ and status):
        return (
            jsonify({"error": "Missing required fields: name, type, status"}),
            400,
        )

    pet_id = generate_pet_id()
    pet_data = {
        "id": pet_id,
        "name": name,
        "type": type_,
        "status": status,
        "photoUrls": photo_urls,
    }
    _local_pet_store[pet_id] = pet_data
    logger.info(f"Pet added locally: {pet_id} - {name}")
    return jsonify({"id": pet_id, "message": "Pet added successfully"}), 201


@app.route("/pets", methods=["GET"])
async def get_all_pets():
    """
    Retrieve all pets stored locally.
    """
    pets = list(_local_pet_store.values())
    return jsonify({"pets": pets})


@app.route("/pets/<pet_id>", methods=["GET"])
async def get_pet_by_id(pet_id):
    """
    Retrieve details of a single pet by its ID (local).
    """
    pet = _local_pet_store.get(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404
    return jsonify(pet)


@app.route("/pets/<pet_id>/status", methods=["POST"])
async def update_pet_status(pet_id):
    """
    Update pet status locally.
    Request body:
    {
        "status": "string"
    }
    """
    pet = _local_pet_store.get(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404

    data = await request.get_json(force=True)
    status = data.get("status")
    if not status:
        return jsonify({"error": "Missing status field"}), 400

    pet["status"] = status
    logger.info(f"Updated pet {pet_id} status to {status}")
    return jsonify({"id": pet_id, "message": "Status updated successfully"})


if __name__ == '__main__':
    import sys
    import logging

    # Setup basic logging to stdout
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
