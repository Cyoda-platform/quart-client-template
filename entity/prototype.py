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

# In-memory "cache" for pets and adoption requests per run
# Structure:
# pets_cache = {
#   "pets": [...],
#   "favorites": set(petIds),
#   "last_updated": datetime
# }
pets_cache: Dict = {"pets": [], "favorites": set(), "last_updated": None}

# Adoption requests just stored locally for prototype
adoption_requests: List[Dict] = []

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

##########
# Helpers
##########


async def fetch_pets_from_petstore(
    pet_type: Optional[str],
    status: Optional[str],
) -> List[Dict]:
    """
    Fetch pets from Petstore API filtered by status.
    Petstore API does not support filtering by type directly,
    so filtering by type will happen locally.

    Petstore API endpoint: /pet/findByStatus?status={status}
    """
    # Validate status param for Petstore API: available, pending, sold
    valid_statuses = {"available", "pending", "sold"}
    statuses = [status] if status in valid_statuses else list(valid_statuses)

    pets = []
    async with httpx.AsyncClient() as client:
        for stat in statuses:
            try:
                resp = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params={"status": stat})
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, list):
                    pets.extend(data)
                else:
                    logger.warning(f"Unexpected Petstore response format for status={stat}: {data}")
            except Exception as e:
                logger.exception(f"Error fetching pets from Petstore for status={stat}: {e}")

    # Filter by type locally if pet_type specified and not 'all'
    if pet_type and pet_type.lower() != "all":
        filtered = [p for p in pets if p.get("category", {}).get("name", "").lower() == pet_type.lower()]
    else:
        filtered = pets

    # Normalize pets to expected schema
    normalized_pets = []
    for pet in filtered:
        normalized_pets.append(
            {
                "id": str(pet.get("id", "")),
                "name": pet.get("name", ""),
                "type": pet.get("category", {}).get("name", "other").lower(),
                "status": pet.get("status", "available"),
                "photoUrls": pet.get("photoUrls", []),
                "isFavorite": False,  # will update below
            }
        )
    return normalized_pets


async def process_fetch_request(data: Dict) -> Dict:
    """
    Process POST /pets/fetch business logic:
    - fetch from Petstore API with filters
    - apply actions (markFavorite, updateAdoptionStatus)
    - cache results locally
    """
    filter_ = data.get("filter", {})
    actions = data.get("actions", {})

    pet_type = filter_.get("type", "all")
    status = filter_.get("status", "all")

    pets = await fetch_pets_from_petstore(pet_type, status)

    # Update favorites from cache first
    favorites = pets_cache.get("favorites", set())

    # Apply markFavorite action
    mark_fav_list = actions.get("markFavorite", [])
    for pet_id in mark_fav_list:
        favorites.add(pet_id)

    # Apply updateAdoptionStatus action
    # TODO: For prototype, we just update status locally in pets list
    update_status_dict = actions.get("updateAdoptionStatus", {})
    for pet in pets:
        if pet["id"] in update_status_dict:
            pet["status"] = update_status_dict[pet["id"]]

    # Update isFavorite flag per pet
    for pet in pets:
        pet["isFavorite"] = pet["id"] in favorites

    # Update cache - replace all pets and favorites
    pets_cache["pets"] = pets
    pets_cache["favorites"] = favorites
    pets_cache["last_updated"] = datetime.utcnow()

    return {"pets": pets, "message": "Pets fetched and processed successfully."}


async def process_adoption_request(data: Dict) -> Dict:
    """
    Process POST /pets/adopt:
    - Store adoption request in local cache
    - TODO: Add notifications or external system integration
    """
    pet_id = data.get("petId")
    adopter = data.get("adopter", {})
    name = adopter.get("name")
    contact = adopter.get("contact")

    if not pet_id or not name or not contact:
        return {"success": False, "message": "Missing petId or adopter info."}

    # Check pet exists in cache
    pet_ids = {p["id"] for p in pets_cache.get("pets", [])}
    if pet_id not in pet_ids:
        return {"success": False, "message": "Pet not found in current data."}

    # Save adoption request locally
    adoption_requests.append(
        {
            "petId": pet_id,
            "adopter": {"name": name, "contact": contact},
            "requestedAt": datetime.utcnow().isoformat(),
        }
    )
    logger.info(f"New adoption request: petId={pet_id}, adopter={name}")

    # TODO: Trigger notifications or update pet status in real system

    return {"success": True, "message": f"Adoption request for pet {pet_id} received."}


##########
# Routes
##########


@app.route("/pets/fetch", methods=["POST"])
async def pets_fetch():
    try:
        data = await request.get_json(force=True)
        # Fire and forget processing task - but here we await it to return results immediately for prototype
        result = await process_fetch_request(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal Server Error"}), 500


@app.route("/pets", methods=["GET"])
async def pets_get():
    pets = pets_cache.get("pets", [])
    return jsonify({"pets": pets})


@app.route("/pets/adopt", methods=["POST"])
async def pets_adopt():
    try:
        data = await request.get_json(force=True)
        result = await process_adoption_request(data)
        return jsonify(result)
    except Exception as e:
        logger.exception(e)
        return jsonify({"success": False, "message": "Internal Server Error"}), 500


if __name__ == "__main__":
    # Run Quart app with specified parameters
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
