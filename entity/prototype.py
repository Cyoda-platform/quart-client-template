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

# Request schemas
@dataclass
class PetSearch:
    type: Optional[str] = None
    status: Optional[str] = None

@dataclass
class PetFavorite:
    petId: int
    favorite: bool

@dataclass
class PetDetails:
    petId: int

# In-memory caches
favorites_cache: Dict[int, Dict] = {}
entity_jobs: Dict[str, Dict] = {}

PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"

async def fetch_pets(type_: str = None, status: str = None) -> List[Dict]:
    params = {}
    if status:
        params["status"] = status
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params=params)
            resp.raise_for_status()
            pets = resp.json()
            if type_:
                pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == type_.lower()]
            return pets
        except Exception as e:
            logger.exception(f"Error fetching pets from Petstore: {e}")
            return []

async def fetch_pet_details(pet_id: int) -> Dict:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/{pet_id}")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.exception(f"Error fetching pet details for petId={pet_id}: {e}")
            return {}

@app.route("/pets/search", methods=["POST"])
# Workaround due to quart-schema defect: PUT/POST validation must come after route decorator
@validate_request(PetSearch)
async def pets_search(data: PetSearch):
    type_ = data.type
    status = data.status
    logger.info(f"Received /pets/search with type={type_} status={status}")
    pets = await fetch_pets(type_, status)
    pets_response = []
    for pet in pets:
        pets_response.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name"),
            "status": pet.get("status"),
            "photoUrls": pet.get("photoUrls", []),
        })
    return jsonify({"pets": pets_response})

@app.route("/pets/favorite", methods=["POST"])
# Workaround: validate_request must be last decorator for POST
@validate_request(PetFavorite)
async def pets_favorite(data: PetFavorite):
    pet_id = data.petId
    favorite = data.favorite
    logger.info(f"Received /pets/favorite for petId={pet_id} favorite={favorite}")
    if favorite:
        requested_at = datetime.utcnow().isoformat()
        job_id = f"fav_add_{pet_id}_{requested_at}"
        entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}
        async def process_favorite_add(job_id_, pet_id_):
            try:
                pet_details = await fetch_pet_details(pet_id_)
                if pet_details and pet_details.get("id"):
                    favorites_cache[pet_id_] = {
                        "id": pet_details.get("id"),
                        "name": pet_details.get("name"),
                        "type": pet_details.get("category", {}).get("name"),
                        "status": pet_details.get("status"),
                        "photoUrls": pet_details.get("photoUrls", []),
                    }
                entity_jobs[job_id_]["status"] = "completed"
            except Exception as e:
                logger.exception(e)
                entity_jobs[job_id_]["status"] = "failed"
        asyncio.create_task(process_favorite_add(job_id, pet_id))
        return jsonify({"success": True, "message": "Pet favorite request accepted"})
    else:
        if pet_id in favorites_cache:
            favorites_cache.pop(pet_id)
            return jsonify({"success": True, "message": "Pet unfavorited"})
        else:
            return jsonify({"success": False, "message": "Pet was not favorited"}), 404

@app.route("/pets/favorites", methods=["GET"])
async def pets_favorites():
    fav_list = list(favorites_cache.values())
    logger.info(f"Returning {len(fav_list)} favorite pets")
    return jsonify({"favorites": fav_list})

@app.route("/pets/details", methods=["POST"])
# Workaround: validate_request must be last decorator for POST
@validate_request(PetDetails)
async def pets_details(data: PetDetails):
    pet_id = data.petId
    logger.info(f"Received /pets/details for petId={pet_id}")
    pet_details = await fetch_pet_details(pet_id)
    if not pet_details or pet_details.get("id") is None:
        return jsonify({"error": "Pet not found"}), 404
    return jsonify(pet_details)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)