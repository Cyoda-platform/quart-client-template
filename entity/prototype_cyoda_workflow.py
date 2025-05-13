import asyncio
import logging
from datetime import datetime

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
    Modify entity state or perform async tasks related to this entity.
    Do NOT add/update/delete entities of the same model here to avoid recursion.
    """

    # Add or update a 'last_modified' timestamp
    entity['last_modified'] = datetime.utcnow().isoformat() + 'Z'

    # Set created_at timestamp if not present
    if 'created_at' not in entity:
        entity['created_at'] = datetime.utcnow().isoformat() + 'Z'

    # Example async fire-and-forget enrichment task
    async def enrich_entity():
        try:
            # Simulate async I/O, e.g. fetch external metadata or validation
            await asyncio.sleep(0.1)
            # Modify entity safely in async context
            entity['enriched'] = True
        except Exception as e:
            logger.error(f"Enrichment task failed: {e}")

    # Run enrichment task concurrently without awaiting - fire and forget
    asyncio.create_task(enrich_entity())

    # Example: Add supplementary entity of a different entity_model (allowed)
    # Uncomment and customize if needed
    # try:
    #     await entity_service.add_item(
    #         token=cyoda_auth_service,
    #         entity_model="pet_metadata",
    #         entity_version=ENTITY_VERSION,
    #         entity={"pet_id": entity.get("id"), "metadata": "example"},
    #         workflow=None
    #     )
    # except Exception as e:
    #     logger.error(f"Failed to add supplementary pet_metadata entity: {e}")

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
        logger.exception("Failed to add pet via entity_service")
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
        logger.exception("Failed to fetch pets via entity_service")
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
        logger.exception("Failed to retrieve pet via entity_service")
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
        logger.exception("Failed to delete pet via entity_service")
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