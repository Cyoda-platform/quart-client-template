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

# In-memory cache to mock persistence (per "no global" - use an asyncio.Lock and dict inside app context)
class Cache:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._pets: List[Dict] = []
        self._last_updated: Optional[datetime] = None

    async def update_pets(self, pets: List[Dict]):
        async with self._lock:
            self._pets = pets
            self._last_updated = datetime.utcnow()

    async def get_pets(self) -> List[Dict]:
        async with self._lock:
            return self._pets.copy()

cache = Cache()

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

# Fun pet facts (static sample data)
FUN_FACTS = {
    "cat": [
        "Cats sleep for 70% of their lives.",
        "A group of cats is called a clowder.",
        "Cats have five toes on their front paws, but only four on the back."
    ],
    "dog": [
        "Dogs have three eyelids.",
        "Dogs can learn more than 1000 words.",
        "A dog's sense of smell is 40 times better than humans."
    ],
    "all": [
        "Pets can reduce stress and anxiety.",
        "Owning a pet can improve heart health.",
        "Many pets have unique ways of showing affection."
    ]
}

async def fetch_pets_from_petstore(pet_type: Optional[str], status: Optional[str]) -> List[Dict]:
    """
    Fetch pets from the Petstore API, filtering by type and status if provided.
    Petstore API endpoint: GET /pet/findByStatus?status=available
    We will ignore "type" filter as Petstore API does not support it directly,
    so we filter results locally.
    """
    params = {}
    if status:
        params["status"] = status
    else:
        # Petstore requires status param for this endpoint, so default to 'available'
        params["status"] = "available"

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params=params, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(e)
            return []

    # Filter by type if requested
    if pet_type and pet_type.lower() != "all":
        pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == pet_type.lower()]

    # Map data to simplified schema
    mapped_pets = []
    for pet in pets:
        mapped_pets.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name"),
            "status": pet.get("status"),
            "photoUrls": pet.get("photoUrls", []),
        })
    return mapped_pets


@app.route("/pets/fetch", methods=["POST"])
async def pets_fetch():
    """
    Fetch pets from external Petstore API based on filters.
    """
    data = await request.get_json(silent=True) or {}
    pet_type = data.get("type")
    status = data.get("status")

    pets = await fetch_pets_from_petstore(pet_type, status)
    await cache.update_pets(pets)

    return jsonify({
        "success": True,
        "pets": pets,
        "message": "Data fetched from Petstore API"
    })


@app.route("/pets/fun-fact", methods=["POST"])
async def pets_fun_fact():
    """
    Return a random fun fact about pets, optionally filtered by type.
    """
    import random

    data = await request.get_json(silent=True) or {}
    pet_type = data.get("type", "all").lower()

    facts_pool = FUN_FACTS.get(pet_type, FUN_FACTS["all"])
    fun_fact = random.choice(facts_pool) if facts_pool else "Pets are awesome!"

    return jsonify({
        "success": True,
        "funFact": fun_fact
    })


@app.route("/pets", methods=["GET"])
async def pets_get():
    """
    Retrieve last fetched pet data stored in the app.
    """
    pets = await cache.get_pets()
    return jsonify({
        "success": True,
        "pets": pets
    })


@app.route("/pets/match", methods=["POST"])
async def pets_match():
    """
    Provide a pet recommendation based on user preferences.
    Match a pet from cached pets by preferredType and preferredStatus.
    If none found, return a message accordingly.
    """
    data = await request.get_json(silent=True) or {}
    preferred_type = (data.get("preferredType") or "").lower()
    preferred_status = (data.get("preferredStatus") or "").lower()

    pets = await cache.get_pets()

    # Filter pets by preferences
    filtered = pets
    if preferred_type:
        filtered = [p for p in filtered if (p.get("type") or "").lower() == preferred_type]
    if preferred_status:
        filtered = [p for p in filtered if (p.get("status") or "").lower() == preferred_status]

    if filtered:
        # Simple recommendation: pick a random pet from filtered list
        import random
        recommended_pet = random.choice(filtered)
        return jsonify({
            "success": True,
            "recommendedPet": recommended_pet
        })
    else:
        return jsonify({
            "success": False,
            "message": "No pet matches your preferences. Try fetching pets first or change filters."
        })


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
