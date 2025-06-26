```python
import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Local in-memory caches (async-safe with asyncio.Lock)
search_cache = {"data": None, "lock": asyncio.Lock()}
favorites_cache = {"data": set(), "lock": asyncio.Lock()}

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"


async def fetch_pets_from_petstore(type_: str | None, status: str | None):
    params = {}
    if status:
        params["status"] = status
    # Petstore API does not support filtering by type directly; we fetch all and filter manually
    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets = resp.json()
            if type_:
                pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == type_.lower()]
            return pets
        except httpx.HTTPError as e:
            logger.exception("Error fetching pets from Petstore API")
            return []


async def fetch_pet_details_from_petstore(pet_id: int):
    url = f"{PETSTORE_BASE_URL}/pet/{pet_id}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.exception(f"Error fetching pet details for id {pet_id}")
            return None


@app.route("/pets/search", methods=["POST"])
async def search_pets():
    data = await request.get_json(force=True)
    type_ = data.get("type")
    status = data.get("status")

    pets = await fetch_pets_from_petstore(type_, status)

    # Cache the last search result (thread-safe)
    async with search_cache["lock"]:
        search_cache["data"] = pets

    return jsonify({"pets": pets})


@app.route("/pets", methods=["GET"])
async def get_last_search():
    async with search_cache["lock"]:
        pets = search_cache["data"]
    if pets is None:
        return jsonify({"pets": []})
    return jsonify({"pets": pets})


@app.route("/pets/details", methods=["POST"])
async def pet_details():
    data = await request.get_json(force=True)
    pet_id = data.get("id")
    if not isinstance(pet_id, int):
        return jsonify({"error": "Invalid or missing pet id"}), 400

    pet = await fetch_pet_details_from_petstore(pet_id)
    if pet is None:
        return jsonify({"error": "Pet not found"}), 404

    # Add optional description if none exists - TODO: Petstore API does not provide description, consider enriching here
    if "description" not in pet:
        pet["description"] = ""

    return jsonify(pet)


@app.route("/pets/favorites", methods=["GET"])
async def get_favorites():
    async with favorites_cache["lock"]:
        fav_ids = list(favorites_cache["data"])

    # Fetch pet details for favorites in parallel
    async def fetch_one(pet_id):
        pet = await fetch_pet_details_from_petstore(pet_id)
        if pet:
            # Return minimal info for favorites list
            return {
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name"),
                "status": pet.get("status"),
            }
        return None

    pets = await asyncio.gather(*(fetch_one(pid) for pid in fav_ids))
    pets = [p for p in pets if p is not None]

    return jsonify({"favorites": pets})


@app.route("/pets/favorites", methods=["POST"])
async def add_favorite():
    data = await request.get_json(force=True)
    pet_id = data.get("id")
    if not isinstance(pet_id, int):
        return jsonify({"error": "Invalid or missing pet id"}), 400

    # Validate pet exists before adding
    pet = await fetch_pet_details_from_petstore(pet_id)
    if pet is None:
        return jsonify({"error": "Pet not found"}), 404

    async with favorites_cache["lock"]:
        favorites_cache["data"].add(pet_id)

    response = {
        "message": "Pet added to favorites",
        "pet": {
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name"),
            "status": pet.get("status"),
        },
    }
    return jsonify(response)


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
