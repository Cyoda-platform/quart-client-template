import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class PetSearch:
    type: Optional[str] = None
    status: Optional[str] = None

# workaround: validate_request must be placed after @app.route for POST due to quart-schema defect
@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearch)
async def pets_search(data: PetSearch):
    """
    POST /pets/search
    Accepts optional filters: type, status
    Fetches pets from Petstore API filtered by status (Petstore API supports status filter)
    Since Petstore API does not support type filtering natively, filter client-side.
    Caches results in memory.
    """
    try:
        pet_type = data.type
        status = data.status

        async with httpx.AsyncClient() as client:
            params = {}
            if status:
                params["status"] = status
            else:
                params["status"] = "available"
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params=params)
            resp.raise_for_status()
            pets_raw = resp.json()

        if pet_type:
            pets_filtered = [p for p in pets_raw if p.get("category") and p["category"].get("name", "").lower() == pet_type.lower()]
        else:
            pets_filtered = pets_raw

        pets = []
        for p in pets_filtered:
            pets.append({
                "id": p.get("id"),
                "name": p.get("name"),
                "type": p.get("category", {}).get("name", None),
                "status": p.get("status"),
                "photoUrls": p.get("photoUrls", []),
            })

        await cache.set_pets(pets)
        return jsonify({"pets": pets})

    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to fetch pets"}), 500

# POST /pets/fun-fact has no body, so no validation needed
@app.route("/pets/fun-fact", methods=["POST"])
async def pets_fun_fact():
    import random
    fact = random.choice(FUN_PET_FACTS)
    return jsonify({"fact": fact})

# GET endpoints serve cached data only; validation for GET should be first if needed (none needed here)
@app.route("/pets", methods=["GET"])
async def get_cached_pets():
    pets = await cache.get_pets()
    if pets is None:
        return jsonify({"error": "No cached pets data found. Please perform a search first."}), 404
    return jsonify({"pets": pets})

@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_cached_pet_by_id(pet_id: int):
    pet = await cache.get_pet_by_id(pet_id)
    if pet is None:
        return jsonify({"error": f"Pet with id {pet_id} not found in cache."}), 404
    return jsonify(pet)

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)