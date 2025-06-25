```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory async-safe cache for favorites and adoption status
# Using asyncio.Lock to avoid race conditions
favorites_lock = asyncio.Lock()
favorites_cache: Dict[str, List[Dict]] = {}  # userName -> list of favorite pets

adoption_lock = asyncio.Lock()
adoption_status: Dict[str, str] = {}  # petId -> status ("available", "adopted")

# Petstore API base URL
PETSTORE_API = "https://petstore.swagger.io/v2"


async def fetch_pets_from_petstore(
    type_: str = None, breed: str = None, name: str = None
) -> List[Dict]:
    """
    Fetch pets from Petstore API by filtering on type, breed, or name.
    Petstore API doesn't directly support breed or name filtering,
    so we filter client-side after fetching all pets by status=available.

    TODO: Petstore API is limited; breed and name filtering is client-side.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Petstore API sample: GET /pet/findByStatus?status=available
            resp = await client.get(f"{PETSTORE_API}/pet/findByStatus", params={"status": "available"})
            resp.raise_for_status()
            pets = resp.json()
    except Exception as e:
        logger.exception(f"Failed to fetch pets from Petstore: {e}")
        return []

    # Filter client-side
    filtered = []
    for pet in pets:
        # pet['category']['name'] might be type (dog, cat, etc) - optional
        pet_type = pet.get("category", {}).get("name", "").lower() if pet.get("category") else ""
        pet_name = pet.get("name", "").lower()
        # Petstore API doesn't have breed field, we skip breed filtering
        if type_ and type_.lower() != pet_type:
            continue
        if name and name.lower() not in pet_name:
            continue
        filtered.append(
            {
                "id": str(pet.get("id")),
                "name": pet.get("name", ""),
                "type": pet_type,
                "breed": "",  # TODO: breed info not available in Petstore API
                "age": 0,  # TODO: no age info in Petstore API
                "status": adoption_status.get(str(pet.get("id")), "available"),
            }
        )
    return filtered


async def adopt_pet(pet_id: str, user_name: str) -> bool:
    """
    Mark pet as adopted if available, else return False.
    No real update to Petstore API since it's a mock API.

    This simulates adoption by updating in-memory adoption_status.
    """
    async with adoption_lock:
        current_status = adoption_status.get(pet_id, "available")
        if current_status != "available":
            return False
        adoption_status[pet_id] = "adopted"
    logger.info(f"User '{user_name}' adopted pet {pet_id}")
    return True


async def add_favorite_pet(pet_id: str, user_name: str, pet_info: Dict) -> None:
    """
    Add a pet to the user's favorites in the in-memory cache.
    """
    async with favorites_lock:
        user_favs = favorites_cache.setdefault(user_name, [])
        # Avoid duplicates
        if not any(fav.get("id") == pet_id for fav in user_favs):
            user_favs.append(pet_info)
            logger.info(f"Pet {pet_id} added to favorites for user '{user_name}'")


@app.route("/pets/search", methods=["POST"])
async def pets_search():
    """Search pets by type, breed, or name. External call happens here."""
    data = await request.get_json(force=True)
    type_ = data.get("type")
    breed = data.get("breed")  # breed filtering is not supported in Petstore API
    name = data.get("name")

    pets = await fetch_pets_from_petstore(type_, breed, name)
    return jsonify({"pets": pets})


@app.route("/pets/adopt", methods=["POST"])
async def pets_adopt():
    """Request adoption of a pet."""
    data = await request.get_json(force=True)
    pet_id = data.get("petId")
    user_name = data.get("userName")

    if not pet_id or not user_name:
        return jsonify({"success": False, "message": "Missing petId or userName"}), 400

    success = await adopt_pet(pet_id, user_name)
    if success:
        return jsonify({"success": True, "message": "Adoption request confirmed."})
    else:
        return jsonify({"success": False, "message": "Pet is not available for adoption."}), 409


@app.route("/pets/favorites/add", methods=["POST"])
async def pets_favorites_add():
    """Add pet to user's favorites."""
    data = await request.get_json(force=True)
    pet_id = data.get("petId")
    user_name = data.get("userName")

    if not pet_id or not user_name:
        return jsonify({"success": False, "message": "Missing petId or userName"}), 400

    # Fetch pet info from Petstore for favorite details
    pets = await fetch_pets_from_petstore()
    pet_info = next((p for p in pets if p["id"] == pet_id), None)
    if not pet_info:
        return jsonify({"success": False, "message": "Pet not found"}), 404

    await add_favorite_pet(pet_id, user_name, pet_info)
    return jsonify({"success": True, "message": "Pet added to favorites."})


@app.route("/pets/favorites", methods=["GET"])
async def pets_favorites():
    """Retrieve user's favorite pets."""
    user_name = request.args.get("userName")
    if not user_name:
        return jsonify({"favorites": []})  # Empty list if no userName query param

    async with favorites_lock:
        favs = favorites_cache.get(user_name, [])

    return jsonify({"favorites": favs})


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
