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

# Local async-safe cache containers
# Using asyncio.Lock to avoid race condition in async context
class AsyncCache:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._pets: List[Dict] = []

    async def set_pets(self, pets: List[Dict]):
        async with self._lock:
            self._pets = pets

    async def get_pets(self, type_filter: Optional[str] = None, status_filter: Optional[str] = None) -> List[Dict]:
        async with self._lock:
            result = self._pets
            if type_filter:
                result = [p for p in result if p.get("category", {}).get("name", "").lower() == type_filter.lower()]
            if status_filter:
                result = [p for p in result if p.get("status", "").lower() == status_filter.lower()]
            return result


pet_cache = AsyncCache()


# Helper: Fire and forget task to fetch and cache pets from Petstore API
async def fetch_and_cache_pets(category: Optional[str], status: Optional[str]):
    url = "https://petstore.swagger.io/v2/pet/findByStatus"
    # According to Petstore API, the `status` param is required and can be comma separated values
    params = {}
    if status:
        params["status"] = status
    else:
        # Default to 'available' if no status given
        params["status"] = "available"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            pets = response.json()

            # Petstore pets have "category" object, filter by category name if provided
            if category:
                pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == category.lower()]

            # Cache pets
            await pet_cache.set_pets(pets)

            logger.info(f"Fetched and cached {len(pets)} pets from Petstore")
            return len(pets)
        except Exception as e:
            logger.exception(f"Failed to fetch pets from Petstore API: {e}")
            return 0


@app.route("/pets/fetch", methods=["POST"])
async def pets_fetch():
    data = await request.get_json(force=True)
    category = data.get("category")
    status = data.get("status")

    requested_at = datetime.utcnow().isoformat()
    job_id = f"job-{requested_at}"

    # Fire and forget fetching pets to avoid blocking client
    asyncio.create_task(fetch_and_cache_pets(category, status))

    return jsonify(
        {
            "message": "Data fetch started; pets will be cached asynchronously",
            "requestedAt": requested_at,
            "jobId": job_id,
        }
    ), 202


@app.route("/pets/recommend", methods=["POST"])
async def pets_recommend():
    data = await request.get_json(force=True)
    prefs = data.get("preferences", {})

    # Retrieve cached pets
    pets = await pet_cache.get_pets()

    # Simple filtering based on preferences
    type_pref = prefs.get("type")
    age_range = prefs.get("ageRange")
    friendly = prefs.get("friendly")

    filtered = pets
    if type_pref:
        filtered = [p for p in filtered if p.get("category", {}).get("name", "").lower() == type_pref.lower()]
    if age_range and len(age_range) == 2:
        min_age, max_age = age_range
        # Petstore pets don't have explicit age, so we use tags or name for demo purposes
        # TODO: Replace with real age field if available
        # For prototype: filter by presence of "ageX" tag (mock)
        def age_tag_filter(pet):
            # Try to parse age from tags like "age3" (mocked)
            tags = pet.get("tags") or []
            for tag in tags:
                if tag.get("name", "").startswith("age"):
                    try:
                        age = int(tag["name"][3:])
                        return min_age <= age <= max_age
                    except Exception:
                        continue
            return True  # If no age info, include anyway

        filtered = [p for p in filtered if age_tag_filter(p)]

    if friendly is not None:
        # No friendly info in Petstore API, so filter randomly or skip
        # TODO: Replace with real friendly info if available
        pass

    # Limit recommendations to 5
    recommendations = []
    for pet in filtered[:5]:
        recommendations.append(
            {
                "id": pet.get("id"),
                "name": pet.get("name"),
                "age": None,  # TODO: no real age info in Petstore API
                "type": pet.get("category", {}).get("name"),
            }
        )

    return jsonify({"recommendations": recommendations})


@app.route("/pets", methods=["GET"])
async def pets_get():
    type_filter = request.args.get("type")
    status_filter = request.args.get("status")

    pets = await pet_cache.get_pets(type_filter=type_filter, status_filter=status_filter)

    # Return simplified pet info
    pets_out = [
        {
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name"),
            "status": pet.get("status"),
        }
        for pet in pets
    ]
    return jsonify({"pets": pets_out})


@app.route("/pets/funfact", methods=["POST"])
async def pets_funfact():
    data = await request.get_json(force=True)
    pet_type = data.get("type", "").lower()

    # Simple hardcoded fun facts for demonstration
    fun_facts = {
        "cat": "Cats have five toes on their front paws, but only four on the back.",
        "dog": "Dogs have three eyelids, including one to keep their eyes moist.",
        "bird": "Some birds can see ultraviolet light, which humans cannot.",
    }

    fun_fact = fun_facts.get(pet_type, "Every pet is unique and full of surprises!")

    return jsonify({"funFact": fun_fact})


if __name__ == "__main__":
    import sys

    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
