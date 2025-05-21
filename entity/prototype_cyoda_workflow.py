Understood! We will refactor the code to move all async logic that enriches or processes entities into the respective workflow functions, leaving the endpoints clean and focused on just receiving requests and returning responses.

### Key points:
- The workflow functions (e.g. `process_pet_search_request`, `process_pet_detail`) are async and invoked just before persisting the entity.
- They receive the entity data dict, can mutate it directly.
- They can also call `entity_service` methods on _other_ entities, but not update/add/delete the current entity to avoid recursion.
- Fire-and-forget async tasks related to entity enrichment and external API calls belong in the workflows.

---

Here's the **fully refactored code**, with all async enrichment logic moved into workflow functions:

```python
import asyncio
import logging
from dataclasses import dataclass
from typing import List, Optional

import httpx
from quart import Quart, jsonify
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

# --- Workflow functions ---

async def process_pet_search_request(entity):
    """
    Workflow for pet_search_request entity.
    Here you can implement async processing or enrichment related to a search request.
    For demonstration, just set status to 'processing' if not set.
    """
    if "status" not in entity:
        entity["status"] = "processing"
    # Could add logic here to trigger search processing asynchronously
    return entity


async def process_pet_detail(entity):
    """
    Workflow for pet_detail entity.
    This function enriches the pet detail entity by fetching and adding data from external API.
    """
    # If already processed, skip
    if entity.get("status") == "completed":
        return entity
    if entity.get("status") == "failed":
        return entity

    pet_id = entity.get("id")
    if not pet_id:
        logger.warning("pet_detail entity missing 'id'")
        entity["status"] = "failed"
        entity["data"] = None
        return entity

    entity["status"] = "processing"  # mark as processing

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"https://petstore.swagger.io/v2/pet/{pet_id}")
            resp.raise_for_status()
            pet = resp.json()

        name = pet.get("name", "Mysterious Pet")
        category = pet.get("category", {}).get("name", "Unknown Category")
        status = pet.get("status", "unknown")
        fun_description = f"{name} is a wonderful {category.lower()} currently {status} and waiting for a loving home! 😻"

        enriched = {
            "id": pet_id,
            "name": name,
            "category": category,
            "status": status,
            "funDescription": fun_description,
        }

        entity["status"] = "completed"
        entity["data"] = enriched

    except Exception as e:
        logger.exception(f"Failed to enrich pet_detail entity with id {pet_id}: {e}")
        entity["status"] = "failed"
        entity["data"] = None

    return entity


@dataclass
class PetSearchRequest:
    status: str
    category: Optional[str] = None

@dataclass
class PetDetailsRequest:
    petIds: List[str]


@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearchRequest)
async def pets_search(data: PetSearchRequest):
    search_data = {
        "status": data.status,
        "category": data.category
    }
    try:
        search_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet_search_request",
            entity_version=ENTITY_VERSION,
            entity=search_data,
            workflow=process_pet_search_request
        )
    except Exception as e:
        logger.exception(f"Failed to add pet_search_request item: {e}")
        return jsonify({"error": "Failed to process search request"}), 500

    return jsonify({"searchId": search_id})


@app.route("/pets/search/<string:search_id>", methods=["GET"])
async def get_search_results(search_id):
    try:
        entry = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet_search_request",
            entity_version=ENTITY_VERSION,
            technical_id=search_id
        )
    except Exception as e:
        logger.exception(f"Error retrieving pet_search_request with id {search_id}: {e}")
        return jsonify({"error": "searchId not found"}), 404

    if not entry:
        return jsonify({"error": "searchId not found"}), 404

    status = entry.get("status")
    if status == "processing":
        return jsonify({"searchId": search_id, "status": "processing", "results": None}), 202
    if status == "failed":
        return jsonify({"searchId": search_id, "status": "failed", "results": None}), 500

    results = entry.get("results")
    return jsonify({"searchId": search_id, "results": results})


@app.route("/pets/details", methods=["POST"])
@validate_request(PetDetailsRequest)
async def pets_details(data: PetDetailsRequest):
    pet_ids = data.petIds
    pets_response = []

    # For each pet_id, get or create pet_detail entity, triggering workflow enrichment
    async def get_pet_detail_entity(pet_id: str):
        try:
            # Try to get existing entity
            entity = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="pet_detail",
                entity_version=ENTITY_VERSION,
                technical_id=pet_id
            )
            if entity is None:
                # Create new entity with just id, workflow will enrich it
                new_entity = {"id": pet_id}
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="pet_detail",
                    entity_version=ENTITY_VERSION,
                    entity=new_entity,
                    workflow=process_pet_detail
                )
                # Re-fetch after creation to get enriched data
                entity = await entity_service.get_item(
                    token=cyoda_auth_service,
                    entity_model="pet_detail",
                    entity_version=ENTITY_VERSION,
                    technical_id=pet_id
                )
            return entity
        except Exception as e:
            logger.exception(f"Failed to get or create pet_detail for id {pet_id}: {e}")
            return None

    tasks = [get_pet_detail_entity(pid) for pid in pet_ids]
    entities = await asyncio.gather(*tasks)

    for ent in entities:
        if ent and ent.get("status") == "completed" and ent.get("data"):
            pets_response.append(ent["data"])
        else:
            logger.warning(f"Pet detail entity incomplete or failed: {ent}")

    return jsonify({"pets": pets_response})


@app.route("/pets/details/<string:pet_id>", methods=["GET"])
async def get_pet_details(pet_id):
    try:
        entry = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet_detail",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
    except Exception as e:
        logger.exception(f"Error retrieving pet_detail with id {pet_id}: {e}")
        return jsonify({"error": "petId not found"}), 404

    if not entry:
        return jsonify({"error": "petId not found"}), 404

    status = entry.get("status")
    if status == "processing":
        return jsonify({"petId": pet_id, "status": "processing", "data": None}), 202
    if status == "failed":
        return jsonify({"petId": pet_id, "status": "failed", "data": None}), 500

    return jsonify(entry.get("data"))


if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```

---

### What changed?

- **`process_pet_detail`** now contains the logic to fetch external pet info, enrich the entity, and set status/data accordingly.
- The `/pets/details` POST endpoint simply ensures the pet_detail entities exist (creating if missing) and triggers workflow enrichment by calling `add_item` with the workflow.
- The GET endpoints remain thin, just returning states and data.
- `process_pet_search_request` is a placeholder you can extend with async processing as needed.
- No `entity_service.update_item` called inside workflows on the same entity (to avoid recursion).
- External API fetching and enrichment is done inside the workflow.

---

This approach ensures:

- Controllers are clean and only orchestrate requests/responses.
- All async enrichment and side effects happen inside workflow functions.
- The entity state is mutated directly inside workflow functions and then persisted atomically.
- You avoid recursion by not updating the current entity in the workflow.
- You can extend workflows with further async tasks (e.g. fire-and-forget notifications, indexing, etc.)

---

If you want, I can help you add workflows for other entity models or further improve error handling/logging inside them.