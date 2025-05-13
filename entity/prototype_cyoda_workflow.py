Certainly! Below is the updated complete code for `entity/prototype_cyoda.py` with the required changes:

- Added a workflow function called `process_pet` that takes the entity data as argument and can modify it asynchronously before persistence.
- Passed this function as the `workflow` parameter to `entity_service.add_item`.

```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema
from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

entity_name = "pet"  # entity name always underscore lowercase

# --- Workflow function ---

async def process_pet(entity: dict) -> dict:
    """
    Workflow function applied to the pet entity asynchronously before persistence.
    You can modify the entity state here, e.g., add timestamps, default values, etc.
    """
    # Example: add or update a 'last_modified' timestamp
    entity['last_modified'] = datetime.utcnow().isoformat() + 'Z'

    # You can add more logic here if needed

    return entity

# --- Routes ---

@app.route("/pets", methods=["POST"])
async def add_update_pet():
    """
    Add or update pet.
    POST body is dynamic, no validation decorator used.
    """
    data = await request.get_json()
    if not data:
        return jsonify({"error": "Empty request body"}), 400

    try:
        # Add item via entity_service, passing the workflow function
        new_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=data,
            workflow=process_pet
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add pet via entity_service"}), 502

    # Return only the id, do not retrieve the item immediately
    return jsonify({"id": str(new_id), "message": "Pet added successfully"}), 200

@app.route("/pets/search", methods=["POST"])
async def search_pets_by_status():
    """
    Search pets by status via external Petstore API.
    """
    data = await request.get_json()
    if not data or "status" not in data:
        return jsonify({"error": "Missing 'status' field in request body"}), 400

    status_list = data.get("status")
    if not isinstance(status_list, list) or not all(isinstance(s, str) for s in status_list):
        return jsonify({"error": "'status' must be a list of strings"}), 400

    # Build condition for entity_service.get_items_by_condition
    condition = {
        "pet": {
            "type": "group",
            "operator": "AND",
            "conditions": [
                {
                    "jsonPath": "$.status",
                    "operatorType": "IN",
                    "value": status_list,
                    "type": "simple"
                }
            ]
        }
    }

    try:
        pets = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            condition=condition
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to fetch pets via entity_service"}), 502

    return jsonify(pets), 200

@app.route("/pets/<pet_id>", methods=["GET"])
async def get_pet(pet_id: str):
    """
    Retrieve pet details from entity_service by string id.
    """
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pet via entity_service"}), 502

    if not pet:
        return jsonify({"error": "Pet not found"}), 404

    return jsonify(pet), 200

@app.route("/pets/<pet_id>/delete", methods=["POST"])
async def delete_pet(pet_id: str):
    """
    Delete pet by ID via entity_service.
    """
    try:
        await entity_service.delete_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
            meta={}
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to delete pet via entity_service"}), 502

    return jsonify({"message": "Pet deleted successfully"}), 200


if __name__ == '__main__':
    import sys

    # Simple console handler for logging
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```

---

**Explanation:**

- The new async function `process_pet` is defined at module level, named with the required prefix `process_` followed by the entity name `pet` in lowercase underscore.
- This function accepts the entity data dictionary, modifies or enriches it (example provided adds a timestamp), and returns it.
- In the route `/pets` inside `add_update_pet()`, the call to `entity_service.add_item` now includes the `workflow=process_pet` argument.
- All other parts of the code remain unchanged.

Let me know if you need further customization!