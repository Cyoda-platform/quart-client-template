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

# Local in-memory cache for favorites per "user"
# NOTE: This is a simple prototype-level cache, not thread-safe for real usage
favorites_cache: Dict[str, Dict[int, dict]] = {}

PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"


async def fetch_pets_from_petstore(
    filters: dict, sort_by: Optional[str], sort_order: Optional[str], limit: int, offset: int
) -> dict:
    """
    Fetch pets from Petstore API applying filters on category and status.
    Petstore API does not provide complex filtering/sorting directly,
    so this prototype fetches all pets and applies filtering/sorting locally.
    TODO: Optimize with Petstore API filter params if available.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Petstore API: GET /pet/findByStatus?status={status}
            status = filters.get("status")
            if status:
                url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
                params = {"status": status}
                response = await client.get(url, params=params)
            else:
                # No status filter: fallback to get pets by all statuses (available, pending, sold)
                # This is a limitation of the Petstore API, so we aggregate results
                pets = []
                for s in ["available", "pending", "sold"]:
                    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
                    response = await client.get(url, params={"status": s})
                    if response.status_code == 200:
                        pets.extend(response.json())
                # Filter by category locally below after this block
                response = None
            if response and response.status_code == 200:
                pets = response.json()
            elif response:
                logger.error(f"Petstore API error: {response.status_code} {response.text}")
                pets = []
        except Exception as e:
            logger.exception(f"Error fetching pets from Petstore API: {e}")
            pets = []

    # Filter by category locally
    category_filter = filters.get("category")
    if category_filter:
        pets = [
            pet
            for pet in pets
            if pet.get("category") and pet["category"].get("name", "").lower() == category_filter.lower()
        ]

    # Sort locally if requested
    if sort_by:
        reverse = sort_order == "desc"
        # We sort by fields present in the pet object or nested (e.g. name, category.name)
        def sort_key(p):
            if sort_by == "category":
                return p.get("category", {}).get("name", "").lower()
            return p.get(sort_by, "")

        pets.sort(key=sort_key, reverse=reverse)

    total_count = len(pets)
    pets = pets[offset : offset + limit]

    # Normalize pet structure to match response model
    result_pets = []
    for p in pets:
        result_pets.append(
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "category": p.get("category", {}).get("name"),
                "status": p.get("status"),
                "photoUrls": p.get("photoUrls", []),
                "tags": [t["name"] for t in p.get("tags", []) if "name" in t],
            }
        )

    return {"pets": result_pets, "total_count": total_count}


@app.route("/pets/query", methods=["POST"])
async def pets_query():
    """
    POST /pets/query
    Body: filters, sort_by, sort_order, limit, offset
    """
    data = await request.get_json()
    filters = data.get("filters", {})
    sort_by = data.get("sort_by")
    sort_order = data.get("sort_order", "asc")
    limit = data.get("limit", 10)
    offset = data.get("offset", 0)

    logger.info(f"Received pet query: filters={filters}, sort_by={sort_by}, sort_order={sort_order}, limit={limit}, offset={offset}")

    pets_data = await fetch_pets_from_petstore(filters, sort_by, sort_order, limit, offset)

    return jsonify(pets_data)


def get_user_id() -> str:
    """
    Prototype user identification - for now, always returns a fixed user id.
    TODO: Implement real user authentication and identification.
    """
    return "default_user"


@app.route("/favorites/add", methods=["POST"])
async def favorites_add():
    """
    POST /favorites/add
    Body: pet_id
    """
    data = await request.get_json()
    pet_id = data.get("pet_id")

    if not isinstance(pet_id, int):
        return jsonify({"success": False, "message": "Invalid or missing pet_id"}), 400

    user_id = get_user_id()
    user_favorites = favorites_cache.setdefault(user_id, {})

    if pet_id in user_favorites:
        return jsonify({"success": False, "message": "Pet already in favorites"}), 400

    # TODO: Optionally verify pet_id exists in Petstore API

    # Add pet_id placeholder, details can be fetched later or stored on add
    user_favorites[pet_id] = {"added_at": datetime.utcnow().isoformat()}

    logger.info(f"User {user_id} added pet {pet_id} to favorites")
    return jsonify({"success": True, "message": "Pet added to favorites."})


@app.route("/favorites/remove", methods=["POST"])
async def favorites_remove():
    """
    POST /favorites/remove
    Body: pet_id
    """
    data = await request.get_json()
    pet_id = data.get("pet_id")

    if not isinstance(pet_id, int):
        return jsonify({"success": False, "message": "Invalid or missing pet_id"}), 400

    user_id = get_user_id()
    user_favorites = favorites_cache.setdefault(user_id, {})

    if pet_id not in user_favorites:
        return jsonify({"success": False, "message": "Pet not in favorites"}), 400

    user_favorites.pop(pet_id)

    logger.info(f"User {user_id} removed pet {pet_id} from favorites")
    return jsonify({"success": True, "message": "Pet removed from favorites."})


@app.route("/favorites", methods=["GET"])
async def favorites_list():
    """
    GET /favorites
    Returns full pet info for favorite pets by querying Petstore API.
    """
    user_id = get_user_id()
    user_favorites = favorites_cache.get(user_id, {})

    if not user_favorites:
        return jsonify({"favorites": []})

    pet_ids = list(user_favorites.keys())

    # Fetch pet details concurrently
    async with httpx.AsyncClient(timeout=10.0) as client:

        async def fetch_pet(pet_id: int):
            try:
                url = f"{PETSTORE_BASE_URL}/pet/{pet_id}"
                r = await client.get(url)
                if r.status_code == 200:
                    p = r.json()
                    return {
                        "id": p.get("id"),
                        "name": p.get("name"),
                        "category": p.get("category", {}).get("name"),
                        "status": p.get("status"),
                        "photoUrls": p.get("photoUrls", []),
                    }
                else:
                    logger.warning(f"Petstore API returned {r.status_code} for pet {pet_id}")
                    return None
            except Exception as e:
                logger.exception(f"Error fetching pet {pet_id} details: {e}")
                return None

        pet_details_results = await asyncio.gather(*[fetch_pet(pid) for pid in pet_ids])
        favorites = [pet for pet in pet_details_results if pet is not None]

    return jsonify({"favorites": favorites})


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
