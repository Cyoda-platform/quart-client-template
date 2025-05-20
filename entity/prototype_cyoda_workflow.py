Understood. The goal is to refactor the existing code to move as much asynchronous logic as possible out of the controller endpoints and into the dedicated asynchronous workflow functions named `process_{entity_name}`. These workflow functions will be called right before the entity is persisted, allowing us to:

- Modify the entity data in-place before saving.
- Perform async tasks like fetching or adding supplementary entities of different models.
- Avoid controller bloat and make the API endpoints lightweight.

---

### Which logic to move?

Looking at the current code:

- `/pets/search` endpoint calls `entity_service.add_item` with the filters entity and the workflow function. This is already mostly clean.
- `/pets/results` endpoint currently:
  - Retrieves all `pet_search_filters` entities.
  - Picks the latest one.
  - Builds a search condition based on filter attributes.
  - Retrieves pets matching the condition.
  - Returns the pet list.
  
- `/pets/details` endpoint:
  - Retrieves a pet entity by ID.
  - Returns the pet details.

---

### What can move into workflow functions?

1. For `pet_search_filters` entity (`process_pet_search_filters`):

   - We currently only add a timestamp, but we can extend this to do more prep work if needed.
   - This is already fine.

2. For the search results, we currently do the retrieval and filtering inside the endpoint. However, the `pet_search_filters` entity is just the input filters, and the actual search results are a derived entity.

   Since the workflow function is invoked *before* persisting the entity, and the `pet_search_filters` entity itself is just filters, we cannot update/search the pets entity inside the same workflow to avoid recursion. But we can create a **new supplementary entity** like `pet_search_results` inside the workflow that contains the actual results of the search. This offloads the search logic into the workflow.

   So the flow becomes:

   - `/pets/search` adds a `pet_search_filters` entity with filters.
   - `process_pet_search_filters` runs:
     - Runs the search query on `pet` entities with the filters.
     - Adds a new entity `pet_search_results` with the search results, linked to the `pet_search_filters` entity.
     - Possibly updates some attributes on the filter entity (e.g. status or timestamp).

3. For `/pets/results` endpoint:

   - Instead of querying `pet_search_filters` and searching pets, it just retrieves the latest `pet_search_results` entity and returns it.
   - This makes the endpoint very simple.

4. For `/pets/details`:

   - It just fetches the pet entity by ID — this is already simple and directly returns it.
   - No complex logic to move here.

---

### Summary of refactoring plan:

- **`process_pet_search_filters`**:
  - Runs pet search based on filters.
  - Stores results in a new entity `pet_search_results`.
  - Updates filter entity state (e.g. processed timestamp).

- **`/pets/search`** endpoint:
  - Only adds `pet_search_filters` entity with workflow attached.

- **`/pets/results`** endpoint:
  - Fetches latest `pet_search_results` entity.
  - Returns the pet list.

- **`/pets/details`** endpoint:
  - No change.

---

### Implementation details

- We add a new entity model `pet_search_results`.
- The workflow function will call `entity_service.get_items_by_condition` to fetch pets.
- Then it will add a new entity `pet_search_results` with the results and a reference to the filter entity id.
- The results endpoint will return these saved results.
- This approach decouples search filter saving from actual search execution and results fetching.

---

### Full updated code with these changes:

```python
import asyncio
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

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
class PetSearchFilters:
    type: Optional[str] = None
    status: Optional[str] = None
    breed: Optional[str] = None

@dataclass
class PetDetailsRequest:
    pet_id: str  # id as string

# Workflow function for pet_search_filters entity
async def process_pet_search_filters(entity_data):
    """
    Workflow function called before persisting pet_search_filters entity.
    It performs the pet search based on filters, and stores results
    in a new pet_search_results entity.
    """
    # Add processed timestamp
    entity_data["processed_at"] = datetime.utcnow().isoformat()

    # Build condition for pet search based on filters
    conditions = []

    if entity_data.get("status"):
        conditions.append({
            "jsonPath": "$.status",
            "operatorType": "EQUALS",
            "value": entity_data["status"],
            "type": "simple"
        })

    if entity_data.get("type"):
        conditions.append({
            "jsonPath": "$.category.name",
            "operatorType": "IEQUALS",
            "value": entity_data["type"],
            "type": "simple"
        })

    if entity_data.get("breed"):
        # Assuming breed is stored in pet name? Adjust if needed.
        conditions.append({
            "jsonPath": "$.name",
            "operatorType": "IEQUALS",
            "value": entity_data["breed"],
            "type": "simple"
        })

    condition = {
        "cyoda": {
            "type": "group",
            "operator": "AND",
            "conditions": conditions
        }
    }

    # Perform pet search async
    pets = await entity_service.get_items_by_condition(
        token=cyoda_auth_service,
        entity_model="pet",
        entity_version=ENTITY_VERSION,
        condition=condition
    )

    # Prepare pet results data
    pet_results = []
    for pet in pets:
        pet_results.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name"),
            "breed": pet.get("name"),
            "status": pet.get("status"),
            "photoUrls": pet.get("photoUrls", [])
        })

    # Save pet search results as a new entity linked to this search filter
    # We use add_item without workflow to avoid recursion
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet_search_results",
            entity_version=ENTITY_VERSION,
            entity={
                "search_filter_id": entity_data.get("id"),  # may be None before persist, but some systems assign id before workflow
                "timestamp": datetime.utcnow().isoformat(),
                "results": pet_results
            },
            workflow=None  # no workflow here
        )
    except Exception as e:
        logger.error(f"Failed to save pet_search_results entity: {e}")

    # No need to return anything; modifications to entity_data are saved


@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearchFilters)
async def pets_search(data: PetSearchFilters):
    filters = {k: v for k, v in data.__dict__.items() if v is not None}
    entity_name = "pet_search_filters"
    # Add filters entity with workflow to do search and save results
    id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model=entity_name,
        entity_version=ENTITY_VERSION,
        entity=filters,
        workflow=process_pet_search_filters
    )
    return jsonify({"jobId": id, "status": "processing"}), 202


@app.route("/pets/results", methods=["GET"])
async def pets_results():
    """
    Retrieve latest pet search results from pet_search_results entity.
    """
    try:
        # Get all pet_search_results
        results_entities = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet_search_results",
            entity_version=ENTITY_VERSION,
        )
        if not results_entities:
            return jsonify({"pets": []})

        # Get latest results by timestamp
        latest_results_entity = max(results_entities, key=lambda x: x.get("timestamp", ""))
        pets = latest_results_entity.get("results", [])

        return jsonify({"pets": pets})

    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve results"}), 500


@app.route("/pets/details", methods=["POST"])
@validate_request(PetDetailsRequest)
async def pets_details(data: PetDetailsRequest):
    pet_id = str(data.pet_id)
    try:
        pet_details = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
        if not pet_details:
            return jsonify({"error": "Pet not found"}), 404

        response = {
            "id": pet_details.get("id"),
            "name": pet_details.get("name"),
            "type": pet_details.get("category", {}).get("name"),
            "breed": pet_details.get("name"),
            "status": pet_details.get("status"),
            "photoUrls": pet_details.get("photoUrls", []),
            "description": pet_details.get("tags", [{}])[0].get("name", "")
        }
        return jsonify(response)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pet details"}), 500


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```

---

### What changed?

- **Moved the pet search logic from `/pets/results` endpoint into `process_pet_search_filters` workflow function.**
- **`process_pet_search_filters` performs the pet search and saves the results in a new `pet_search_results` entity asynchronously before the filters entity is persisted.**
- **The `/pets/results` endpoint now simply fetches the latest `pet_search_results` entity and returns the results.**
- This makes the controller endpoints lightweight and the async logic centralized in the workflow.
- Added error handling in the workflow when saving results.
- No infinite recursion because workflow is only applied to `pet_search_filters` entity, and results are saved in a different entity model without a workflow.

---

### Additional notes

- The entity ID (`entity_data.get("id")`) inside the workflow might be None if the backend assigns the ID after workflow processing. If that is the case, you might want to link the results entity with some other unique identifier or timestamp only.
- You can extend `process_pet_search_filters` to do more async tasks if needed (logging, enrichment, validation).
- This pattern can be repeated for other entities if you want to move async logic out of controllers.

---

Please let me know if you want me to do the same pattern for other entities / endpoints or add further improvements!