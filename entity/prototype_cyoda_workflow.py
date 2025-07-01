Understood. We want to move all business logic, especially async tasks (including fire-and-forget style ones), from the endpoints/controllers into the `process_{entity_name}` workflow functions. This will clean up the controllers and make the processing robust and reusable.

---

### Summary of what to move into `process_pet` (workflow function):

- The logic that enriches or modifies the `pet` entity before persistence.
- Fire-and-forget async tasks related to pets, for example fetching supplementary data or adding related entities.
- Any data transformation or validation that can be done at the entity level.
  
---

### What we **cannot** do inside `process_pet`:

- We **cannot** call `add_item`, `update_item`, or `delete_item` on the same entity model ("pet") to avoid infinite recursion.
- However, we **can** call those on other entity models if needed.
- We **can** modify the entity dictionary directly to update its state.

---

### What should remain in the endpoints:

- Receive and validate input.
- Call `entity_service.add_item` / `update_item` / `get_item` with the workflow function.
- Return response.

---

### Plan for refactoring:

- The existing `process_pet` will be extended to handle more logic like:
  - Adding timestamps.
  - Normalizing tags.
  - Any enrichment or secondary entity creation related to pets.
- The existing async fetch job for pets is currently a separate fire-and-forget task. We'll move that logic into a new workflow function `process_fetch_pets_job` is a special case that is not related to a single entity but a job. So it can remain as is.
- For endpoints that add or update pets, move the transformation logic inside `process_pet`.
- Remove direct transformation logic from endpoints.

---

### Implementation:

```python
from dataclasses import dataclass
from typing import Optional, List

import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

entity_jobs = {}

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

async def fetch_pets_from_petstore(filter_status, filter_category):
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            url = f"{PETSTORE_API_BASE}/pet/findByStatus"
            params = {"status": filter_status or "available"}
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets = resp.json()
            if filter_category:
                pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == filter_category.lower()]
            return pets
        except Exception as e:
            logger.exception("Failed to fetch pets from Petstore API")
            return []

async def process_pet(entity: dict) -> dict:
    """
    Workflow function for 'pet' entity.
    Modify the entity state here before persistence if needed.
    This includes normalizing tags, adding timestamps, or adding related entities.
    """
    # Normalize tags to list (ensure always list of strings)
    if "tags" not in entity or not isinstance(entity["tags"], list):
        entity["tags"] = []
    else:
        # Clean tags to be list of strings, ignoring invalid entries
        entity["tags"] = [str(t) for t in entity["tags"] if t]

    # Add createdAt timestamp if missing
    if "createdAt" not in entity:
        entity["createdAt"] = datetime.utcnow().isoformat()

    # Add updatedAt timestamp on each persistence
    entity["updatedAt"] = datetime.utcnow().isoformat()

    # Example of adding supplementary entities of different model (e.g. "tag") if needed
    # We can add tags as separate entities in another model if wanted, but commented out here:
    #
    # for tag_name in entity["tags"]:
    #     await entity_service.add_item(
    #         token=cyoda_auth_service,
    #         entity_model="tag",
    #         entity_version=ENTITY_VERSION,
    #         entity={"name": tag_name},
    #         workflow=None  # No further workflow to avoid recursion
    #     )
    #
    # But since this is add_item on different model, it is allowed.
    # However, this example is optional and depends on requirements.

    return entity

async def process_pet_update(entity: dict) -> dict:
    """
    Optional separate workflow function for update if needed.
    Here we just reuse process_pet.
    """
    # Could add update-specific logic here
    return await process_pet(entity)

async def process_fetch_pets_job_entity(entity: dict) -> dict:
    """
    Workflow function for a hypothetical 'fetch_pets_job' entity.
    This could kick off the async fetch and add pets asynchronously.
    For demonstration, we'll assume such an entity exists.
    """
    status = entity.get("filter", {}).get("status")
    category = entity.get("filter", {}).get("category")

    # Fire and forget: fetch pets async and add them as pet entities
    async def fetch_and_add():
        pets = await fetch_pets_from_petstore(status, category)
        for pet in pets:
            try:
                pet_data = {
                    "name": pet.get("name"),
                    "category": pet.get("category", {}).get("name"),
                    "status": pet.get("status"),
                    "tags": [t.get("name") for t in pet.get("tags", []) if t.get("name")]
                }
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="pet",
                    entity_version=ENTITY_VERSION,
                    entity=pet_data,
                    workflow=process_pet
                )
            except Exception:
                logger.exception("Failed to add pet in fetch job workflow")

    asyncio.create_task(fetch_and_add())

    # Update job entity state to reflect job started
    entity["status"] = "processing"
    entity["requestedAt"] = datetime.utcnow().isoformat()

    return entity


@dataclass
class Filter:
    status: str
    category: Optional[str] = None

@dataclass
class FetchPetsRequest:
    filter: Filter

@dataclass
class AddPetRequest:
    name: str
    category: str
    status: str
    tags: List[str]

@dataclass
class UpdatePetRequest:
    name: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)
async def pets_fetch(data: FetchPetsRequest):
    # Create a job entity that triggers the fetch pets async via workflow
    job_entity = {
        "filter": {
            "status": data.filter.status,
            "category": data.filter.category,
        }
    }
    job_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="fetch_pets_job",
        entity_version=ENTITY_VERSION,
        entity=job_entity,
        workflow=process_fetch_pets_job_entity
    )
    return jsonify({"message": "Data fetch initiated", "job_id": str(job_id)})

@app.route("/pets", methods=["GET"])
async def list_pets():
    try:
        pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
        )
        return jsonify(pets)
    except Exception as e:
        logger.exception("Failed to list pets")
        return jsonify({"message": "Failed to list pets"}), 500

@app.route("/pets/add", methods=["POST"])
@validate_request(AddPetRequest)
async def add_pet(data: AddPetRequest):
    pet_data = {
        "name": data.name,
        "category": data.category,
        "status": data.status,
        "tags": data.tags,
    }
    try:
        pet_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=pet_data,
            workflow=process_pet
        )
        logger.info(f"Added pet {pet_id}")
        return jsonify({"message": "Pet added successfully", "pet_id": str(pet_id)})
    except Exception as e:
        logger.exception("Failed to add pet")
        return jsonify({"message": "Failed to add pet"}), 500

@app.route("/pets/<string:pet_id>", methods=["GET"])
async def get_pet(pet_id):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
        )
        if not pet:
            return jsonify({"message": "Pet not found"}), 404
        return jsonify(pet)
    except Exception as e:
        logger.exception(f"Failed to get pet {pet_id}")
        return jsonify({"message": "Failed to get pet"}), 500

@app.route("/pets/update/<string:pet_id>", methods=["POST"])
@validate_request(UpdatePetRequest)
async def update_pet(data: UpdatePetRequest, pet_id):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
        )
        if not pet:
            return jsonify({"message": "Pet not found"}), 404

        # Update pet dict with new data if present
        if data.name is not None:
            pet["name"] = data.name
        if data.category is not None:
            pet["category"] = data.category
        if data.status is not None:
            pet["status"] = data.status
        if data.tags is not None:
            pet["tags"] = data.tags

        # Use update workflow here by updating via update_item without workflow (assuming update_item doesn't take workflow)
        # Since update_item does not accept workflow arg, all logic must be done here before calling update_item.

        # Instead, let's reuse process_pet logic manually before update:
        pet = await process_pet(pet)

        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=pet,
            technical_id=pet_id,
            meta={}
        )
        logger.info(f"Updated pet {pet_id}")
        return jsonify({"message": "Pet updated successfully"})
    except Exception as e:
        logger.exception(f"Failed to update pet {pet_id}")
        return jsonify({"message": "Failed to update pet"}), 500

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```

---

### Explanation:

- **`process_pet`**:
  - Normalizes tags, adds timestamps, can add related secondary entities (commented example).
  - This logic was earlier in endpoints, now fully inside workflow.
- **`process_fetch_pets_job_entity`**:
  - New workflow function for the `fetch_pets_job` entity model.
  - Starts fire-and-forget async task to fetch pets from Petstore API and add them asynchronously with their own workflow.
  - Updates job entity status.
- **Endpoints**:
  - Now only create entities and assign workflows.
  - No longer contain business logic or async fire-and-forget calls.
- **Update endpoint**:
  - Since `update_item` does not accept a workflow, the workflow logic is manually applied before update by calling `process_pet`.
  - This ensures consistency between add and update.

---

This approach centralizes all mutable entity logic in workflow functions, freeing controllers from business rules and async concerns. It also leverages the new `workflow` argument to run async code directly before persistence.

Let me know if you want me to help with similar refactorings for other entity models or further improvements!