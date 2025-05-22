from dataclasses import dataclass, asdict
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Dataclasses for request validation
@dataclass
class PetFetchFilter:
    type: str
    status: str

@dataclass
class PetFetchActions:
    markFavorite: Optional[List[str]] = None
    updateAdoptionStatus: Optional[Dict[str, str]] = None

@dataclass
class FetchRequest:
    filter: PetFetchFilter
    actions: PetFetchActions

@dataclass
class Adopter:
    name: str
    contact: str

@dataclass
class AdoptRequest:
    petId: str
    adopter: Adopter

# In-memory cache for prototype
pets_cache: Dict = {"pets": [], "favorites": set(), "last_updated": None}
adoption_requests: List[Dict] = []

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

async def fetch_pets_from_petstore(pet_type: Optional[str], status: Optional[str]) -> List[Dict]:
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
            except Exception as e:
                logger.exception(f"Error fetching pets status={stat}: {e}")
    if pet_type and pet_type.lower() != "all":
        pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == pet_type.lower()]
    normalized = []
    for pet in pets:
        normalized.append({
            "id": str(pet.get("id", "")),
            "name": pet.get("name", ""),
            "type": pet.get("category", {}).get("name", "other").lower(),
            "status": pet.get("status", "available"),
            "photoUrls": pet.get("photoUrls", []),
            "isFavorite": False,
        })
    return normalized

async def process_fetch_request(data: Dict) -> Dict:
    filter_ = data.get("filter", {})
    actions = data.get("actions", {})
    pet_type = filter_.get("type", "all")
    status = filter_.get("status", "all")
    pets = await fetch_pets_from_petstore(pet_type, status)
    favorites = pets_cache.get("favorites", set())
    for pet_id in actions.get("markFavorite", []):
        favorites.add(pet_id)
    for pid, new_status in (actions.get("updateAdoptionStatus") or {}).items():
        for pet in pets:
            if pet["id"] == pid:
                pet["status"] = new_status
    for pet in pets:
        pet["isFavorite"] = pet["id"] in favorites
    pets_cache["pets"], pets_cache["favorites"], pets_cache["last_updated"] = pets, favorites, datetime.utcnow()
    return {"pets": pets, "message": "Pets fetched and processed successfully."}

async def process_adoption_request(data: Dict) -> Dict:
    pet_id = data.get("petId")
    adopter = data.get("adopter", {})
    name, contact = adopter.get("name"), adopter.get("contact")
    if not pet_id or not name or not contact:
        return {"success": False, "message": "Missing petId or adopter info."}
    pet_ids = {p["id"] for p in pets_cache.get("pets", [])}
    if pet_id not in pet_ids:
        return {"success": False, "message": "Pet not found in current data."}
    adoption_requests.append({
        "petId": pet_id,
        "adopter": {"name": name, "contact": contact},
        "requestedAt": datetime.utcnow().isoformat(),
    })
    logger.info(f"Adoption requested petId={pet_id}, adopter={name}")
    return {"success": True, "message": f"Adoption request for pet {pet_id} received."}

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchRequest)  # workaround: validate_request must be last for POST due to quart-schema issue
async def pets_fetch(data: FetchRequest):
    try:
        result = await process_fetch_request(asdict(data))
        return jsonify(result)
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal Server Error"}), 500

@app.route("/pets", methods=["GET"])
async def pets_get():
    return jsonify({"pets": pets_cache.get("pets", [])})

@app.route("/pets/adopt", methods=["POST"])
@validate_request(AdoptRequest)  # workaround: validate_request must be last for POST due to quart-schema issue
async def pets_adopt(data: AdoptRequest):
    try:
        result = await process_adoption_request(asdict(data))
        return jsonify(result)
    except Exception as e:
        logger.exception(e)
        return jsonify({"success": False, "message": "Internal Server Error"}), 500

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)