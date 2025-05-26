import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Local in-memory cache to mock persistence
# Structure: { "pets_data": List[Dict], "last_fetched": datetime }
cache: Dict[str, Any] = {
    "pets_data": [],
    "last_fetched": None
}

# Fun facts sample (could be expanded or replaced by dynamic generator)
FUN_FACTS = [
    "Cats sleep 70% of their lives.",
    "Dogs have three eyelids.",
    "Rabbits can see behind them without turning their heads.",
    "Parrots will selflessly help each other.",
    "Guinea pigs communicate with squeaks and purrs."
]

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

async def fetch_pets_from_petstore(category: Optional[str], status: Optional[str]) -> List[Dict]:
    """
    Fetch pets from Petstore API filtered by category and/or status.
    Petstore API reference: https://petstore.swagger.io/#/pet/findPetsByStatus
    Note: The Petstore API does not have a category filter on the pet endpoints,
    so we will filter by status and filter category locally.

    TODO: If category filtering requires external API or another approach, update here.
    """
    url = f"{PETSTORE_API_BASE}/pet/findByStatus"
    params = {}
    if status:
        params["status"] = status
    else:
        # Petstore requires status param, defaulting to available
        params["status"] = "available"

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(f"Error fetching from Petstore API: {e}")
            return []

    # Filter category locally (Petstore pets have 'category' object with 'name')
    if category:
        filtered = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == category.lower()]
        return filtered

    return pets

def add_fun_fact_to_pet(pet: Dict) -> Dict:
    """Add a fun_fact field randomly selected to the pet dictionary."""
    import random

    pet_copy = pet.copy()
    pet_copy["fun_fact"] = random.choice(FUN_FACTS)
    return pet_copy

async def process_fetch_pets(data: Dict[str, Any]) -> None:
    """
    Fetch pets from external API, enrich with fun facts, and store in cache.
    """
    category = data.get("category")
    status = data.get("status")

    pets = await fetch_pets_from_petstore(category, status)
    enriched_pets = [add_fun_fact_to_pet(p) for p in pets]

    # Update cache atomically
    cache["pets_data"] = enriched_pets
    cache["last_fetched"] = datetime.utcnow()

@app.route("/pets/fetch", methods=["POST"])
async def pets_fetch():
    data = await request.get_json(force=True)
    # Start async processing task (fire and forget)
    await process_fetch_pets(data)
    return jsonify({"message": "Pets data fetched and processed."}), 202

@app.route("/pets", methods=["GET"])
async def pets_get():
    pets = cache.get("pets_data", [])
    return jsonify({"pets": pets})

@app.route("/pets/filter", methods=["POST"])
async def pets_filter():
    data = await request.get_json(force=True)
    filter_criteria = data.get("filter", {})
    sort_by = data.get("sort_by")

    pets: List[Dict] = cache.get("pets_data", [])

    # Apply filter
    if filter_criteria:
        def match(pet: Dict) -> bool:
            for key, val in filter_criteria.items():
                # keys expected: category, status
                pet_val = None
                if key == "category":
                    pet_val = pet.get("category", {}).get("name", "").lower()
                else:
                    pet_val = pet.get(key, "").lower()
                if pet_val != val.lower():
                    return False
            return True

        pets = [p for p in pets if match(p)]

    # Apply sort
    if sort_by:
        # Support sorting by "name" or "category" only; ignore others silently
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
    import logging

    # Console handler for logging
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)