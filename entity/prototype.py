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

# In-memory cache for adopted pets and search results to simulate persistence
# Use asyncio.Lock for concurrency safety
class Cache:
    def __init__(self):
        self.adopted_pets: Dict[int, Dict] = {}
        self.lock = asyncio.Lock()

cache = Cache()

PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"


async def fetch_pets_from_petstore(
    type_: Optional[str] = None, status: Optional[str] = None, name: Optional[str] = None
) -> List[Dict]:
    """
    Fetch pets from external Petstore API by criteria.
    This uses Petstore's /pet/findByStatus endpoint if status is provided,
    otherwise fetches all pets and filters locally (Petstore API is limited).
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Petstore API supports findByStatus only
        if status:
            try:
                r = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": status})
                r.raise_for_status()
                pets = r.json()
            except Exception as e:
                logger.exception(f"Error fetching pets by status from Petstore: {e}")
                pets = []
        else:
            # No direct endpoint to fetch all pets, so fallback: try findByStatus with all statuses and merge
            pets = []
            for s in ["available", "pending", "sold"]:
                try:
                    r = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": s})
                    r.raise_for_status()
                    pets.extend(r.json())
                except Exception as e:
                    logger.exception(f"Error fetching pets by status '{s}' from Petstore: {e}")

        # Filter by type and name locally if provided
        def matches_criteria(pet):
            if type_ and pet.get("category", {}).get("name", "").lower() != type_.lower():
                return False
            if name and name.lower() not in pet.get("name", "").lower():
                return False
            return True

        filtered = [pet for pet in pets if matches_criteria(pet)]
        return filtered


def generate_fun_description(pet: Dict) -> str:
    """Generate a fun fact or joke for a pet based on its type or name."""
    # Simple hardcoded fun facts and jokes by pet type, fallback joke
    jokes = {
        "cat": "Did you know cats can make over 100 vocal sounds? Purrhaps it’s true!",
        "dog": "Dogs’ noses are wet to help absorb scent chemicals. Sniff-tastic!",
        "bird": "Birds are the only animals with feathers, they really know how to dress up!",
    }
    pet_type = pet.get("category", {}).get("name", "").lower()
    name = pet.get("name", "Your new friend")
    return jokes.get(pet_type, f"{name} is as awesome as any pet you can imagine!")


@app.route("/pets/search", methods=["POST"])
async def pets_search():
    data = await request.get_json() or {}
    type_ = data.get("type")
    status = data.get("status")
    name = data.get("name")

    pets_raw = await fetch_pets_from_petstore(type_, status, name)

    # Map to response format with fun description
    pets = []
    for p in pets_raw:
        pets.append(
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "type": p.get("category", {}).get("name"),
                "status": p.get("status"),
                "description": generate_fun_description(p),
                "imageUrl": p.get("photoUrls")[0] if p.get("photoUrls") else None,
            }
        )

    return jsonify({"pets": pets})


@app.route("/pets/adopt", methods=["POST"])
async def pets_adopt():
    data = await request.get_json() or {}
    pet_id = data.get("petId")
    if not isinstance(pet_id, int):
        return jsonify({"success": False, "message": "Invalid or missing petId"}), 400

    # Check if pet is available by querying Petstore (simulate business logic)
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(f"{PETSTORE_BASE_URL}/pet/{pet_id}")
            r.raise_for_status()
            pet = r.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return jsonify({"success": False, "message": "Pet not found"}), 404
            logger.exception(e)
            return jsonify({"success": False, "message": "Error fetching pet info"}), 500
        except Exception as e:
            logger.exception(e)
            return jsonify({"success": False, "message": "Error fetching pet info"}), 500

    if pet.get("status") != "available":
        return jsonify({"success": False, "message": "Pet is not available for adoption"}), 400

    # Mark as adopted in local cache
    async with cache.lock:
        if pet_id in cache.adopted_pets:
            return jsonify({"success": False, "message": "Pet already adopted"}), 400
        cache.adopted_pets[pet_id] = {
            "id": pet_id,
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name"),
            "adoptionDate": datetime.utcnow().isoformat() + "Z",
            "message": f"Congratulations on adopting {pet.get('name')}! 🎉🐾",
        }

    return jsonify({"success": True, "message": f"Pet {pet.get('name')} adopted successfully!"})


@app.route("/pets/adopted", methods=["GET"])
async def pets_adopted():
    async with cache.lock:
        adopted_list = list(cache.adopted_pets.values())
    return jsonify({"adoptedPets": adopted_list})


@app.route("/pets/fun-facts", methods=["POST"])
async def pets_fun_facts():
    data = await request.get_json() or {}
    type_ = data.get("type", "").lower() if data.get("type") else None
    name = data.get("name")

    # Simple hardcoded fun facts or jokes
    facts = {
        "cat": "Cats sleep for 70% of their lives. Talk about a catnap!",
        "dog": "Dogs’ sense of smell is at least 40x better than humans’!",
        "bird": "Some birds can mimic human speech amazingly well.",
    }

    if type_ in facts:
        fact = facts[type_]
    elif name:
        fact = f"{name} is truly one of a kind and full of surprises!"
    else:
        fact = "Pets make life pawsome! 🐾😺🐶"

    return jsonify({"fact": fact})


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
