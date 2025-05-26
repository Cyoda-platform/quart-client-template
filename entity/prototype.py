from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Request models
@dataclass
class PetFetchRequest:
    category: Optional[str]
    status: Optional[str]

@dataclass
class PetFilter:
    category: Optional[str]
    status: Optional[str]

@dataclass
class PetFilterRequest:
    filter: PetFilter
    sort_by: Optional[str]

# Local in-memory cache to mock persistence
cache: Dict[str, Any] = {
    "pets_data": [],
    "last_fetched": None
}

FUN_FACTS = [
    "Cats sleep 70% of their lives.",
    "Dogs have three eyelids.",
    "Rabbits can see behind them without turning their heads.",
    "Parrots will selflessly help each other.",
    "Guinea pigs communicate with squeaks and purrs."
]

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

async def fetch_pets_from_petstore(category: Optional[str], status: Optional[str]) -> List[Dict]:
    url = f"{PETSTORE_API_BASE}/pet/findByStatus"
    params = {"status": status or "available"}
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(f"Error fetching from Petstore API: {e}")
            return []
    if category:
        return [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == category.lower()]
    return pets

def add_fun_fact_to_pet(pet: Dict) -> Dict:
    import random
    pet_copy = pet.copy()
    pet_copy["fun_fact"] = random.choice(FUN_FACTS)
    return pet_copy

async def process_fetch_pets(data: Dict[str, Any]) -> None:
    category = data.get("category")
    status = data.get("status")
    pets = await fetch_pets_from_petstore(category, status)
    enriched_pets = [add_fun_fact_to_pet(p) for p in pets]
    cache["pets_data"] = enriched_pets
    cache["last_fetched"] = datetime.utcnow()

@app.route("/pets/fetch", methods=["POST"])
# workaround: place validate_request after route due to quart-schema defect with POST
@validate_request(PetFetchRequest)
async def pets_fetch(data: PetFetchRequest):
    await process_fetch_pets(data.__dict__)
    return jsonify({"message": "Pets data fetched and processed."}), 202

@app.route("/pets", methods=["GET"])
async def pets_get():
    pets = cache.get("pets_data", [])
    return jsonify({"pets": pets})

@app.route("/pets/filter", methods=["POST"])
# workaround: place validate_request after route due to quart-schema defect with POST
@validate_request(PetFilterRequest)
async def pets_filter(data: PetFilterRequest):
    filter_criteria = data.filter.__dict__
    sort_by = data.sort_by
    pets: List[Dict] = cache.get("pets_data", [])

    if filter_criteria:
        def match(pet: Dict) -> bool:
            for key, val in filter_criteria.items():
                pet_val = (pet.get("category", {}).get("name", "").lower() if key == "category"
                           else pet.get(key, "").lower())
                if pet_val != (val or "").lower():
                    return False
            return True
        pets = [p for p in pets if match(p)]

    if sort_by:
        key_func = None
        if sort_by == "name":
            key_func = lambda p: p.get("name", "").lower()
        elif sort_by == "category":
            key_func = lambda p: p.get("category", {}).get("name", "").lower()
        if key_func:
            pets = sorted(pets, key=key_func)

    return jsonify({"pets": pets})

if __name__ == '__main__':
    import sys
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)