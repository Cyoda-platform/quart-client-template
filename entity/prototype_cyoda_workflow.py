Understood! The goal is to refactor so that all async logic, including fire-and-forget tasks, is moved into the workflow functions `process_{entity_name}` that run just before persistence, thus simplifying the endpoints (controllers).

---

### Key points for the refactor:

- The workflow function receives the entity dict before persistence and can mutate it.
- The workflow can perform async operations, including fetching data, calling external APIs, adding/updating other entities (different entity models).
- The workflow **cannot** update/add/delete the **same** entity model to avoid recursion.
- Fire-and-forget jobs (like background fetching/updating) should be done inside the workflow, not the controller.
- Controllers should just prepare the initial entity and call `add_item` with the workflow function, and return immediately.

---

### What we currently do async in endpoints:

- For `"pets_search_job"`:
  - Controller creates initial entity with status=processing and calls `add_item`
  - Controller starts a background task `asyncio.create_task(process_search_job(...))`
  - `process_search_job` fetches pets and updates other entities and finally updates the search job entity with results.

- For `"pets_details"`:
  - Controller checks if details exist; if not, creates initial entity with status=processing and calls `add_item`
  - Controller starts background task `asyncio.create_task(process_details_job(...))`
  - `process_details_job` fetches details and updates pets_details entity.

---

### Refactor plan:

- Remove all background tasks (`asyncio.create_task(...)`) from controllers.
- Move the entire background logic inside the workflow functions:
  - For `"pets_search_job"`, `process_pets_search_job` will:
    - Fetch pets from external API
    - Update `pet` entities with `update_item`
    - Update the current `"pets_search_job"` entity state (modify `entity` dict)
  - For `"pets_details"`, `process_pets_details` will:
    - Fetch pet details from external API
    - Update the current `"pets_details"` entity state (modify `entity` dict)

- Controllers will just create initial "processing" entity and call `add_item` with the workflow function.
- Controllers will return immediately.

---

### Complete updated code with this refactor applied:

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

factory = BeanFactory(config={"CHAT_REPOSITORY": "cyoda"})
entity_service = factory.get_services()["entity_service"]
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

@dataclass
class SearchRequest:
    type: str = None
    status: str = None
    name: str = None

@dataclass
class DetailsRequest:
    petId: int

def generate_id() -> str:
    return str(uuid.uuid4())

PET_ENTITY_NAME = "pet"

async def fetch_pets(filters: dict) -> list:
    status = filters.get("status")
    type_filter = filters.get("type")
    name_filter = filters.get("name")
    url = f"https://petstore3.swagger.io/api/v3/pet/findByStatus"
    params = {"status": status or "available"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            pets = resp.json()
    except Exception as e:
        logger.exception(f"Failed fetching pets: {e}")
        return []
    def matches(p):
        if type_filter and p.get("category", {}).get("name", "").lower() != type_filter.lower():
            return False
        if name_filter and name_filter.lower() not in p.get("name", "").lower():
            return False
        return True
    filtered = [p for p in pets if matches(p)]
    result = []
    for p in filtered:
        result.append({
            "id": str(p.get("id")),
            "name": p.get("name"),
            "type": p.get("category", {}).get("name"),
            "status": p.get("status"),
            "photoUrls": p.get("photoUrls", []),
        })
    return result

async def fetch_pet_details(pet_id: str) -> dict:
    url = f"https://petstore3.swagger.io/api/v3/pet/{pet_id}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            p = resp.json()
    except Exception as e:
        logger.exception(f"Failed fetching details: {e}")
        return {}
    detail = {
        "id": p.get("id"),
        "name": p.get("name"),
        "type": p.get("category", {}).get("name"),
        "status": p.get("status"),
        "photoUrls": p.get("photoUrls", []),
        "description": "No description available.",
        "tags": [t.get("name") for t in p.get("tags", [])] if p.get("tags") else [],
    }
    return detail

# Workflow for pets_search_job entity
async def process_pets_search_job(entity: dict) -> dict:
    search_id = entity.get("searchId")
    filters = {
        "status": entity.get("status"),
        "type": entity.get("type"),
        "name": entity.get("name"),
    }
    logger.info(f"Processing search job {search_id} in workflow")

    pets = await fetch_pets(filters)
    # Update pet entities
    for pet in pets:
        try:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model=PET_ENTITY_NAME,
                entity_version=ENTITY_VERSION,
                entity=pet,
                technical_id=str(pet["id"]),
                meta={},
            )
        except Exception as e:
            logger.exception(f"Failed updating pet {pet['id']} in entity_service: {e}")

    # Update current entity state before persistence
    entity["status"] = "done"
    entity["pets"] = pets
    entity["completedAt"] = datetime.utcnow().isoformat()
    return entity

# Workflow for pets_details entity
async def process_pets_details(entity: dict) -> dict:
    pet_id = str(entity.get("petId"))
    logger.info(f"Processing details job for pet {pet_id} in workflow")

    details = await fetch_pet_details(pet_id)
    entity["status"] = "done"
    entity["details"] = details
    entity["completedAt"] = datetime.utcnow().isoformat()
    return entity


@app.route("/pets/search", methods=["POST"])
@validate_request(SearchRequest)
async def pets_search(data: SearchRequest):
    search_id = generate_id()
    # Prepare initial entity including search filters
    initial_entity = {
        "searchId": search_id,
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "pets": [],
        "type": data.type,
        "name": data.name,
    }
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pets_search_job",
            entity_version=ENTITY_VERSION,
            entity=initial_entity,
            workflow=process_pets_search_job,
        )
    except Exception as e:
        logger.exception(f"Failed creating search job {search_id} in entity_service: {e}")
        return jsonify({"error": "Failed to create search job"}), 500

    return jsonify({"searchId": search_id})


@app.route("/pets/search/<search_id>", methods=["GET"])
async def pets_search_results(search_id):
    try:
        job = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pets_search_job",
            entity_version=ENTITY_VERSION,
            technical_id=search_id,
        )
    except Exception as e:
        logger.exception(f"Failed fetching search job {search_id}: {e}")
        return jsonify({"error": "Search ID not found"}), 404
    if not job:
        return jsonify({"error": "Search ID not found"}), 404
    if job.get("status") != "done":
        return jsonify({"status": job.get("status")}), 202
    return jsonify({"pets": job.get("pets", [])})


@app.route("/pets/details", methods=["POST"])
@validate_request(DetailsRequest)
async def pets_details(data: DetailsRequest):
    pet_id = str(data.petId)
    try:
        job = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pets_details",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
        )
    except Exception as e:
        logger.exception(f"Failed fetching pet details job for {pet_id}: {e}")
        job = None

    if job:
        if job.get("status") == "processing":
            return jsonify({"status": "processing"}), 202
        if job.get("status") == "done":
            return jsonify(job.get("details"))

    # Prepare initial entity for details request with status processing
    initial_entity = {
        "petId": pet_id,
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "details": None,
    }
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pets_details",
            entity_version=ENTITY_VERSION,
            entity=initial_entity,
            workflow=process_pets_details,
        )
    except Exception as e:
        logger.exception(f"Failed creating pet details job for {pet_id}: {e}")
        return jsonify({"error": "Failed to create pet details job"}), 500

    return jsonify({"status": "processing"}), 202


@app.route("/pets/details/<pet_id>", methods=["GET"])
async def pets_details_get(pet_id):
    pet_id = str(pet_id)
    try:
        job = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pets_details",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
        )
    except Exception as e:
        logger.exception(f"Failed fetching pet details for {pet_id}: {e}")
        return jsonify({"error": "Pet details not found"}), 404
    if not job:
        return jsonify({"error": "Pet details not found"}), 404
    if job.get("status") != "done":
        return jsonify({"status": job.get("status")}), 202
    return jsonify(job.get("details"))


if __name__ == "__main__":
    import sys
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```

---

### Explanation of the refactor:

- **Controllers** only create initial entities with `status: processing` and call `entity_service.add_item(...)` with the proper workflow function.
- The workflow functions `process_pets_search_job` and `process_pets_details` contain the full async logic:
  - Fetching from external APIs
  - Updating other entities (`pet` entities for search job)
  - Updating the current entity state (`entity` dict) — modifying status, results, timestamps
- No explicit background tasks or threading in the controller code.
- The workflow function executes asynchronously within `add_item` before persistence, so no recursion occurs because we never call `add/update/delete` on the current entity model inside the workflow.
- This makes the controllers thin and robust and centralizes async logic in workflows.

---

If you want, I can help you test or further modularize the workflow functions. Let me know!