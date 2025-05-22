import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class FetchPetsRequest:
    type: Optional[str]
    status: Optional[str]

@dataclass
class AgeRange:
    min: int
    max: int

@dataclass
class MatchPetsRequest:
    preferredType: str
    ageRange: AgeRange
    status: str

# In-memory async-safe cache for pets data
pets_cache: Dict[int, Dict[str, Any]] = {}
pets_lock = asyncio.Lock()

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

async def fetch_pets_from_petstore(
    pet_type: Optional[str] = None, status: Optional[str] = None
) -> List[Dict[str, Any]]:
    url = f"{PETSTORE_API_BASE}/pet/findByStatus"
    params = {"status": status or "available"}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
            if pet_type:
                pet_type_lower = pet_type.lower()
                filtered = []
                for pet in pets:
                    category = pet.get("category") or {}
                    cat_name = category.get("name", "").lower()
                    if pet_type_lower == "other":
                        if cat_name not in ("cat", "dog"):
                            filtered.append(pet)
                    elif cat_name == pet_type_lower:
                        filtered.append(pet)
                pets = filtered
            return pets
        except Exception as e:
            logger.exception(f"Failed to fetch pets: {e}")
            return []

async def store_pets(pets: List[Dict[str, Any]]):
    async with pets_lock:
        for pet in pets:
            pet_id = pet.get("id")
            if pet_id:
                pets_cache[pet_id] = pet

async def find_pet_matches(
    preferred_type: str, age_min: int, age_max: int, status: str
) -> List[Dict[str, Any]]:
    async with pets_lock:
        results = []
        for pet in pets_cache.values():
            category = pet.get("category") or {}
            pet_type = category.get("name", "").lower() or "other"
            if preferred_type.lower() != pet_type and preferred_type.lower() != "other":
                continue
            pet_status = pet.get("status", "available")
            if pet_status != status:
                continue
            age = 3  # TODO: mock age, Petstore API has no age field
            if age_min <= age <= age_max:
                results.append({
                    "id": pet.get("id"),
                    "name": pet.get("name"),
                    "type": pet_type,
                    "age": age,
                    "status": pet_status,
                })
        return results

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)  # workaround: validation last for POST due to quart-schema issue
async def pets_fetch(data: FetchPetsRequest):
    try:
        pets = await fetch_pets_from_petstore(data.type, data.status)
        await store_pets(pets)
        return jsonify({
            "message": "Pets data fetched successfully",
            "fetchedCount": len(pets),
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to fetch pets"}), 500

@app.route("/pets/match", methods=["POST"])
@validate_request(MatchPetsRequest)  # workaround: validation last for POST due to quart-schema issue
async def pets_match(data: MatchPetsRequest):
    try:
        matches = await find_pet_matches(
            data.preferredType, data.ageRange.min, data.ageRange.max, data.status
        )
        return jsonify({"matches": matches})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to find pet matches"}), 500

@app.route("/pets", methods=["GET"])
async def pets_list():
    try:
        async with pets_lock:
            return jsonify(list(pets_cache.values()))
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
        pet_detail = pet.copy()
        pet_detail["description"] = pet_detail.get(
            "description", "Playful pet who loves attention."
        )  # TODO: mock description, Petstore API has no description field
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