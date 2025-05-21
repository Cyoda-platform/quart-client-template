Absolutely! Moving the asynchronous logic and related state updates from the endpoints into the workflow functions is a cleaner, more robust approach. The workflow functions allow us to handle pre-persistence modifications and side effects, including async operations, without cluttering controller code.

I'll refactor your code accordingly, moving the asynchronous workflows inside the `process_pets_search` and `process_adoptions` functions, and simplifying the endpoints to just pass the initial entity data and let the workflow handle the rest.

---

### Key changes:
- `process_pets_search` will:
  - Fetch pets from petstore API asynchronously.
  - Update the entity's `status`, `pets`, `count`, and `completedAt` fields directly in the entity dict.
  - Since we cannot update the same entity via `entity_service` inside workflow (to avoid recursion), we only mutate the entity dict, which will be persisted once workflow finishes.
  - For supplementary data, if needed, we can add other entities of different models (not used here).
- `process_adoptions` will:
  - Run the adoption processing steps sequentially with async delays.
  - Update the entity's `steps_completed` and `status` fields directly.
  - Since we cannot update the same entity via `entity_service` inside workflow, we mutate the entity dict.
  - For simulating "fire and forget" style progress, we rely on the workflow function's async nature.
- Endpoints just add the initial entity and return the ID, no longer launching background tasks.

---

### Refactored complete code:

```python
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request
from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

# Data classes for request validation
@dataclass
class PetSearchRequest:
    type: Optional[str]
    status: Optional[str]
    tags: Optional[List[str]]

@dataclass
class AdoptionRequest:
    pet_id: str
    adopter_name: str
    contact_info: str

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"


async def fetch_pets_from_petstore(criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        status = criteria.get("status", "available")
        tags = criteria.get("tags", [])
        try:
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": status})
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(f"Error fetching pets from Petstore API: {e}")
            return []

    pet_type = criteria.get("type")
    filtered = []
    for pet in pets:
        if pet_type and pet.get("category", {}).get("name", "").lower() != pet_type.lower():
            continue
        if tags:
            pet_tags = {tag["name"].lower() for tag in pet.get("tags", [])}
            if not all(t.lower() in pet_tags for t in tags):
                continue
        filtered.append(pet)

    return filtered


async def process_pets_search(entity: Dict[str, Any]) -> Dict[str, Any]:
    """
    Workflow function for 'pets_search' entity.
    This function asynchronously fetches pets from petstore and updates the entity accordingly.
    """
    try:
        criteria = entity.get("criteria", {})
        pets = await fetch_pets_from_petstore(criteria)
        entity["status"] = "completed"
        entity["pets"] = pets
        entity["count"] = len(pets)
        entity["completedAt"] = datetime.utcnow().isoformat()
    except Exception as e:
        logger.exception(f"Error in process_pets_search workflow: {e}")
        entity["status"] = "failed"
        entity["error"] = str(e)
    return entity


async def process_adoptions(entity: Dict[str, Any]) -> Dict[str, Any]:
    """
    Workflow function for 'adoptions' entity.
    This function simulates adoption steps sequentially with async delays,
    updating the entity's status and steps_completed fields.
    """
    try:
        steps = [
            "application_received",
            "background_check",
            "adoption_approved",
            "pet_delivered",
            "completed",
        ]
        entity["status"] = "processing"
        entity["steps_completed"] = []

        for step in steps:
            await asyncio.sleep(1)  # simulate async processing delay
            entity["steps_completed"].append(step)
            # Update status to last completed step or 'completed' if done
            entity["status"] = "completed" if step == "completed" else step

    except Exception as e:
        logger.exception(f"Error in process_adoptions workflow: {e}")
        entity["status"] = "failed"
        entity["error"] = str(e)

    return entity


@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearchRequest)
async def pets_search(data: PetSearchRequest):
    criteria = data.__dict__
    search_entry = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "criteria": criteria,
        "pets": [],
        "count": 0,
    }
    try:
        search_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pets_search",
            entity_version=ENTITY_VERSION,
            entity=search_entry,
            workflow=process_pets_search  # Workflow handles async fetching & updating
        )
    except Exception as e:
        logger.exception(f"Error adding pets_search item: {e}")
        return jsonify({"error": "Failed to initiate search"}), 500

    return jsonify({"search_id": search_id, "count": 0}), 202


@app.route("/pets/search/<search_id>", methods=["GET"])
async def get_pets_search_results(search_id):
    try:
        entry = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pets_search",
            entity_version=ENTITY_VERSION,
            technical_id=search_id
        )
    except Exception as e:
        logger.exception(f"Error fetching pets_search item with id {search_id}: {e}")
        return jsonify({"error": "Search ID not found"}), 404

    if not entry:
        return jsonify({"error": "Search ID not found"}), 404

    if entry.get("status") == "processing":
        return jsonify({"status": "processing"}), 202

    pets_resp = []
    for p in entry.get("pets", []):
        pets_resp.append(
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "type": p.get("category", {}).get("name"),
                "status": p.get("status"),
                "tags": [t.get("name") for t in p.get("tags", [])] if p.get("tags") else [],
            }
        )
    return jsonify({"search_id": search_id, "pets": pets_resp})


@app.route("/adoptions", methods=["POST"])
@validate_request(AdoptionRequest)
async def create_adoption(data: AdoptionRequest):
    adoption_entry = {
        "status": "initiated",
        "requestedAt": datetime.utcnow().isoformat(),
        "pet_id": data.pet_id,
        "adopter_name": data.adopter_name,
        "contact_info": data.contact_info,
        "steps_completed": [],
    }
    try:
        adoption_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="adoptions",
            entity_version=ENTITY_VERSION,
            entity=adoption_entry,
            workflow=process_adoptions  # Workflow handles adoption steps progression
        )
    except Exception as e:
        logger.exception(f"Error creating adoption item: {e}")
        return jsonify({"error": "Failed to create adoption"}), 500

    return jsonify({"adoption_id": adoption_id, "status": "initiated"}), 202


@app.route("/adoptions/<adoption_id>", methods=["GET"])
async def get_adoption_status(adoption_id):
    try:
        adoption = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="adoptions",
            entity_version=ENTITY_VERSION,
            technical_id=adoption_id
        )
    except Exception as e:
        logger.exception(f"Error fetching adoption item with id {adoption_id}: {e}")
        return jsonify({"error": "Adoption ID not found"}), 404

    if not adoption:
        return jsonify({"error": "Adoption ID not found"}), 404

    return jsonify(
        {
            "adoption_id": adoption_id,
            "pet_id": adoption.get("pet_id"),
            "adopter_name": adoption.get("adopter_name"),
            "status": adoption.get("status"),
            "steps_completed": adoption.get("steps_completed", []),
        }
    )


if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```

---

### Explanation:

- **Endpoints**: Just create initial entities and specify the workflow function when adding the item. No background tasks or explicit async logic remain.
- **Workflow functions**: `process_pets_search` and `process_adoptions` handle the entire async processing logic, mutate the entity's dictionary directly, which the service will persist after the workflow function completes.
- **No recursion**: We do not call `add_item` or `update_item` on the same entity inside workflow, only mutate the entity dict.
- **Error handling**: Errors inside workflow functions update the entity state to `"failed"` and add an `"error"` message to the entity dict.

This approach fully embraces the new workflow function capability, keeps controllers clean and focused, and ensures all async processing and state updates happen reliably inside the workflow.

Let me know if you want me to also add any supplementary entities or further separate logic inside these workflow functions!