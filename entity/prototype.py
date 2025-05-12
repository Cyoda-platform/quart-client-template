from dataclasses import dataclass
from typing import List, Optional, Dict
import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory "database" mocks
favorites_store: Dict[int, Dict] = {}  # petId -> pet data cache

# External Petstore API base URL (Swagger Petstore public API)
PETSTORE_API_BASE = "https://petstore3.swagger.io/api/v3"

# Sample pet facts for fun feature
PET_FACTS = [
    "Cats sleep 70% of their lives.",
    "Dogs have three eyelids.",
    "Rabbits can see behind them without turning their heads.",
    "Guinea pigs communicate with squeaks and purrs.",
    "Goldfish can recognize their owners."
]

@dataclass
class PetQuery:
    type: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    name: Optional[str] = None

@dataclass
class FavoriteAdd:
    petId: int

@dataclass
class EmptyBody:
    pass

async def fetch_pets_from_petstore(filters: Dict) -> List[Dict]:
    status = filters.get("status", "available")
    url = f"{PETSTORE_API_BASE}/pet/findByStatus"
    params = {"status": status}

    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, params=params, timeout=10)
            r.raise_for_status()
            pets = r.json()
        except Exception as e:
            logger.exception(f"Failed to fetch pets from Petstore API: {e}")
            return []

    filtered = []
    type_filter = filters.get("type")
    tags_filter = set(t.lower() for t in (filters.get("tags") or []))
    name_filter = (filters.get("name") or "").lower()

    for pet in pets:
        pet_type = pet.get("category", {}).get("name")
        if type_filter and (not pet_type or pet_type.lower() != type_filter.lower()):
            continue

        if tags_filter:
            pet_tags = {tag.get("name", "").lower() for tag in pet.get("tags", [])}
            if not tags_filter.issubset(pet_tags):
                continue

        if name_filter and name_filter not in (pet.get("name") or "").lower():
            continue

        filtered.append(
            {
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet_type,
                "status": pet.get("status"),
                "tags": [tag.get("name") for tag in pet.get("tags", [])],
                "photoUrls": pet.get("photoUrls", []),
            }
        )
    return filtered

@app.route("/pets/query", methods=["POST"])
@validate_request(PetQuery)  # POST validation goes last, so decorator goes below route - correct order is route then validate_request
async def pets_query(data: PetQuery):
    pets = await fetch_pets_from_petstore(data.__dict__)
    return jsonify({"pets": pets})

@app.route("/favorites/add", methods=["POST"])
@validate_request(FavoriteAdd)  # POST validation goes last, so decorator goes below route - correct order is route then validate_request
async def favorites_add(data: FavoriteAdd):
    pet_id = data.petId
    if not pet_id or not isinstance(pet_id, int):
        return jsonify({"success": False, "message": "Invalid or missing petId."}), 400

    pet = favorites_store.get(pet_id)
    if not pet:
        pets = await fetch_pets_from_petstore({"status": "available"})
        pet = next((p for p in pets if p["id"] == pet_id), None)
        if not pet:
            return jsonify({"success": False, "message": "Pet not found."}), 404
        favorites_store[pet_id] = pet
    else:
        logger.info(f"Pet {pet_id} already in favorites cache")

    return jsonify({"success": True, "message": "Pet added to favorites."})

# GET /favorites has no input params, so no validation needed
@app.route("/favorites", methods=["GET"])
async def favorites_list():
    return jsonify({"favorites": list(favorites_store.values())})

# POST /fun/random-fact with empty body
@app.route("/fun/random-fact", methods=["POST"])
@validate_request(EmptyBody)  # POST validation goes last, so decorator goes below route - correct order is route then validate_request
async def fun_random_fact(data: EmptyBody):
    import random
    fact = random.choice(PET_FACTS)
    return jsonify({"fact": fact})

if __name__ == "__main__":
    import sys
    import logging

    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        level=logging.INFO,
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```