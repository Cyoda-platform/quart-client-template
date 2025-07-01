from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class QueryPetsRequest:
    category: Optional[str]
    status: Optional[str]
    sort_by: Optional[str]
    sort_order: Optional[str]
    limit: int
    offset: int

@dataclass
class PetIdRequest:
    pet_id: int

favorites_cache: Dict[str, Dict[int, dict]] = {}
PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"

async def fetch_pets_from_petstore(
    filters: dict, sort_by: Optional[str], sort_order: Optional[str], limit: int, offset: int
) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            status = filters.get("status")
            if status:
                url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
                params = {"status": status}
                response = await client.get(url, params=params)
            else:
                pets = []
                for s in ["available", "pending", "sold"]:
                    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
                    r = await client.get(url, params={"status": s})
                    if r.status_code == 200:
                        pets.extend(r.json())
                response = None
            if response and response.status_code == 200:
                pets = response.json()
            elif response:
                logger.error(f"Petstore API error: {response.status_code} {response.text}")
                pets = []
        except Exception as e:
            logger.exception(f"Error fetching pets from Petstore API: {e}")
            pets = []

    category_filter = filters.get("category")
    if category_filter:
        pets = [
            pet
            for pet in pets
            if pet.get("category") and pet["category"].get("name", "").lower() == category_filter.lower()
        ]

    if sort_by:
        reverse = sort_order == "desc"
        def sort_key(p):
            if sort_by == "category":
                return p.get("category", {}).get("name", "").lower()
            return p.get(sort_by, "")
        pets.sort(key=sort_key, reverse=reverse)

    total_count = len(pets)
    pets = pets[offset : offset + limit]

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
@validate_request(QueryPetsRequest)  # validation last for POST due to quart-schema defect
async def pets_query(data: QueryPetsRequest):
    filters = {}
    if data.category:
        filters["category"] = data.category
    if data.status:
        filters["status"] = data.status
    pets_data = await fetch_pets_from_petstore(
        filters, data.sort_by, data.sort_order, data.limit, data.offset
    )
    return jsonify(pets_data)

def get_user_id() -> str:
    return "default_user"

@app.route("/favorites/add", methods=["POST"])
@validate_request(PetIdRequest)  # validation last for POST due to quart-schema defect
async def favorites_add(data: PetIdRequest):
    pet_id = data.pet_id
    user_id = get_user_id()
    user_favorites = favorites_cache.setdefault(user_id, {})
    if pet_id in user_favorites:
        return jsonify({"success": False, "message": "Pet already in favorites"}), 400
    user_favorites[pet_id] = {"added_at": datetime.utcnow().isoformat()}
    logger.info(f"User {user_id} added pet {pet_id} to favorites")
    return jsonify({"success": True, "message": "Pet added to favorites."})

@app.route("/favorites/remove", methods=["POST"])
@validate_request(PetIdRequest)  # validation last for POST due to quart-schema defect
async def favorites_remove(data: PetIdRequest):
    pet_id = data.pet_id
    user_id = get_user_id()
    user_favorites = favorites_cache.setdefault(user_id, {})
    if pet_id not in user_favorites:
        return jsonify({"success": False, "message": "Pet not in favorites"}), 400
    user_favorites.pop(pet_id)
    logger.info(f"User {user_id} removed pet {pet_id} from favorites")
    return jsonify({"success": True, "message": "Pet removed from favorites."})

@app.route("/favorites", methods=["GET"])
async def favorites_list():
    user_id = get_user_id()
    user_favorites = favorites_cache.get(user_id, {})
    if not user_favorites:
        return jsonify({"favorites": []})
    pet_ids = list(user_favorites.keys())
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