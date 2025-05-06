from dataclasses import dataclass
import logging
from datetime import datetime
from typing import Dict

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

@dataclass
class PetIdRequest:
    petId: int

PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"

@app.route("/api/pets/details", methods=["POST"])
@validate_request(PetIdRequest)
async def post_pet_details(data: PetIdRequest):
    pet_id = data.petId
    if not isinstance(pet_id, int) or pet_id <= 0:
        return jsonify({"status": "error", "message": "Invalid petId provided"}), 400

    try:
        existing_items = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            condition={"id": pet_id}
        )
        if existing_items:
            return jsonify({"status": "success", "pet": existing_items[0]}), 200
    except Exception as e:
        logger.exception(f"Error querying existing pet in entity_service: {e}")

    entity = {"id": pet_id}
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=entity,
            )
    except Exception as e:
        logger.exception(f"Error adding pet entity to entity_service: {e}")
        return jsonify({"status": "error", "message": "Failed to initiate pet details processing"}), 500

    return jsonify({
        "status": "processing",
        "message": "Pet details retrieval started asynchronously. Query GET /api/pets/details/{petId} for results.",
        "petId": pet_id
    }), 202

@app.route("/api/pets/details/<int:pet_id>", methods=["GET"])
async def get_pet_details(pet_id: int):
    try:
        items = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            condition={"id": pet_id}
        )
        if not items:
            return jsonify({
                "status": "error",
                "message": "Pet details not found. Please POST to /api/pets/details first."
            }), 404

        pet_entity = items[0]
        return jsonify({"pet": pet_entity}), 200
    except Exception as e:
        logger.exception(f"Error fetching pet details from entity_service: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)