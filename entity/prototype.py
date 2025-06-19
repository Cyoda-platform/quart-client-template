import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class FetchPetsRequest:
    status: Optional[str] = None
    category: Optional[str] = None

@dataclass
class GetPetsQuery:
    status: Optional[str] = None
    category: Optional[str] = None
    limit: int = 20
    offset: int = 0

@dataclass
class AdoptPetRequest:
    petId: int

pets_store: Dict[int, Dict] = {}
pets_store_lock = asyncio.Lock()
PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

async def fetch_pets_from_petstore(status: Optional[str], category: Optional[str]) -> List[Dict]:
    try:
        async with httpx.AsyncClient() as client:
            query_status = status if status else "available,pending,sold"
            url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
            response = await client.get(url, params={"status": query_status})
            response.raise_for_status()
            pets = response.json()
            if category:
                cat_lower = category.lower()
                pets = [
                    pet for pet in pets
                    if pet.get("category", {}).get("name", "").lower() == cat_lower
                ]
            return pets
    except Exception as e:
        logger.exception(f"Failed to fetch pets from Petstore API: {e}")
        return []

async def store_pets(pets: List[Dict]):
    async with pets_store_lock:
        for pet in pets:
            pet_id = pet.get("id")
            if pet_id is not None:
                pets_store[pet_id] = {
                    "id": pet_id,
                    "name": pet.get("name", ""),
                    "category": pet.get("category", {}).get("name", ""),
                    "status": pet.get("status", ""),
                }

async def adopt_pet(pet_id: int) -> Optional[Dict]:
    async with pets_store_lock:
        pet = pets_store.get(pet_id)
        if not pet:
            return None
        pet["status"] = "sold"
        # TODO: Implement external Petstore API update if supported
        return pet

@app.route("/pets/fetch", methods=["POST"])
# workaround: validate_request must come after route for POST due to quart-schema defect
@validate_request(FetchPetsRequest)
async def fetch_pets(data: FetchPetsRequest):
    try:
        requested_at = datetime.utcnow().isoformat()
        logger.info(f"Fetch request at {requested_at} with status={data.status} category={data.category}")
        async def process_fetch():
            pets = await fetch_pets_from_petstore(data.status, data.category)
            await store_pets(pets)
            logger.info(f"Fetched and stored {len(pets)} pets")
        asyncio.create_task(process_fetch())
        return jsonify({"message": "Pets data fetch started asynchronously.", "requestedAt": requested_at}), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to process fetch request"}), 500

@validate_querystring(GetPetsQuery)
@app.route("/pets", methods=["GET"])
# workaround: validate_querystring must come before route for GET due to quart-schema defect
async def get_pets():
    try:
        status = request.args.get("status")
        category = request.args.get("category")
        limit = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))
        async with pets_store_lock:
            pets_list = list(pets_store.values())
        if status:
            sl = status.lower()
            pets_list = [p for p in pets_list if p["status"].lower() == sl]
        if category:
            cl = category.lower()
            pets_list = [p for p in pets_list if p["category"].lower() == cl]
        total = len(pets_list)
        page = pets_list[offset: offset + limit]
        return jsonify({"pets": page, "total": total, "limit": limit, "offset": offset})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pets"}), 500

@app.route("/pets/adopt", methods=["POST"])
# workaround: validate_request must come after route for POST due to quart-schema defect
@validate_request(AdoptPetRequest)
async def adopt(data: AdoptPetRequest):
    try:
        pet = await adopt_pet(data.petId)
        if not pet:
            return jsonify({"error": f"Pet with id {data.petId} not found"}), 404
        return jsonify({"message": f"Pet {data.petId} adopted successfully.", "pet": pet})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to adopt pet"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)