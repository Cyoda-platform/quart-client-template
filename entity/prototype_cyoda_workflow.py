Certainly! I've updated your code to include the `workflow` parameter in `entity_service.add_item` calls and implemented the appropriate workflow function `process_petsearchrequest`. The workflow function asynchronously processes the entity before persistence—here, it performs a pet query with the given filters and adds the resulting pets list into the entity.

Here is the complete updated code with the requested changes:

```python
from dataclasses import dataclass
import asyncio
import logging
import uuid
from datetime import datetime
import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request
from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

@dataclass
class PetSearchRequest:
    type: str = None
    status: str = None
    tags: list[str] = None

@dataclass
class AdoptPetRequest:
    petId: str  # changed to string id
    adopterName: str

class AsyncCache:
    def __init__(self):
        self._adoptions = {}
        self._lock = asyncio.Lock()

    async def add_adoption(self, adopter_name: str, pet: dict):
        async with self._lock:
            if adopter_name not in self._adoptions:
                self._adoptions[adopter_name] = []
            self._adoptions[adopter_name].append(pet)

    async def get_adoptions(self, adopter_name: str):
        async with self._lock:
            return self._adoptions.get(adopter_name, [])

cache = AsyncCache()
PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

async def query_pets(type_: str = None, status: str = None, tags: list[str] = None) -> list[dict]:
    params = {}
    if status:
        params["status"] = status
    url = f"{PETSTORE_API_BASE}/pet/findByStatus"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(f"Failed to fetch pets from external API: {e}")
            return []
    def pet_matches(pet: dict) -> bool:
        if type_ and pet.get("category", {}).get("name", "").lower() != type_.lower():
            return False
        if tags:
            pet_tags = [t.get("name", "").lower() for t in pet.get("tags", [])]
            if not all(t.lower() in pet_tags for t in tags):
                return False
        return True
    return [p for p in pets if pet_matches(p)]

# Workflow function for petsearchrequest entity
async def process_petsearchrequest(entity: dict) -> dict:
    """
    Workflow function applied asynchronously before persisting a petsearchrequest.
    Queries pets based on the filters and adds the resulting list under 'pets' key in the entity.
    """
    pets = await query_pets(entity.get("type"), entity.get("status"), entity.get("tags"))
    entity["pets"] = pets
    return entity

@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearchRequest)
async def pets_search(data: PetSearchRequest):
    # Prepare data dict for entity_service
    data_dict = {
        "type": data.type,
        "status": data.status,
        "tags": data.tags,
    }
    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="petsearchrequest",
            entity_version=ENTITY_VERSION,
            entity=data_dict,
            workflow=process_petsearchrequest  # Added workflow function here
        )
        # return only id, results retrieved via separate endpoint
        return jsonify({"searchId": id})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add pet search request"}), 500

@app.route("/pets/search/<search_id>", methods=["GET"])
async def get_search_results(search_id):
    try:
        result = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="petsearchrequest",
            entity_version=ENTITY_VERSION,
            technical_id=search_id
        )
        if not result:
            return jsonify({"error": "Search ID not found or results not ready"}), 404
        if "pets" in result and result["pets"] is not None:
            pets = result["pets"]
        else:
            pets = await query_pets(result.get("type"), result.get("status"), result.get("tags"))
        simplified = []
        for p in pets:
            simplified.append({
                "id": str(p.get("id")),
                "name": p.get("name"),
                "type": p.get("category", {}).get("name"),
                "status": p.get("status"),
                "tags": [t.get("name") for t in p.get("tags", []) if t.get("name")]
            })
        return jsonify({"searchId": search_id, "pets": simplified})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve search results"}), 500

@app.route("/pets/adopt", methods=["POST"])
@validate_request(AdoptPetRequest)
async def adopt_pet(data: AdoptPetRequest):
    pet_id = data.petId  # already string
    adopter_name = data.adopterName
    pet_info = None
    # Try to find pet info from recent searches
    try:
        all_searches = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="petsearchrequest",
            entity_version=ENTITY_VERSION,
        )
        for search in all_searches:
            pets = None
            if "pets" in search and search["pets"]:
                pets = search["pets"]
            else:
                pets = await query_pets(search.get("type"), search.get("status"), search.get("tags"))
            for pet in pets:
                if str(pet.get("id")) == pet_id:
                    pet_info = {
                        "id": str(pet.get("id")),
                        "name": pet.get("name"),
                        "type": pet.get("category", {}).get("name"),
                        "status": pet.get("status")
                    }
                    break
            if pet_info:
                break
    except Exception as e:
        logger.exception(e)
    if pet_info is None:
        pet_info = {"id": pet_id, "name": None, "type": None, "status": None}
    await cache.add_adoption(adopter_name, pet_info)
    logger.info(f"Pet {pet_id} adopted by {adopter_name}")
    return jsonify({
        "petId": pet_id,
        "adopterName": adopter_name,
        "adoptionStatus": "confirmed"
    })

@app.route("/pets/adoptions/<adopter_name>", methods=["GET"])
async def get_adoptions(adopter_name):
    adopted_pets = await cache.get_adoptions(adopter_name)
    return jsonify({
        "adopterName": adopter_name,
        "adoptedPets": adopted_pets
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```

---

### Summary of changes:

- Added the async workflow function `process_petsearchrequest` that takes an entity dict, queries pets with the filters, and adds the `pets` key to the entity before saving.
- Passed `workflow=process_petsearchrequest` as a parameter to the `entity_service.add_item()` call in `pets_search`.
- No other calls to `add_item` were present so no other changes needed.
- The function and parameter naming strictly follow the underscore lowercase `petsearchrequest` entity name and `process_` prefix rule.

Let me know if you want me to implement workflows for other entities or any other modifications!