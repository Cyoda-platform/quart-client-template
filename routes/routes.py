from datetime import timezone, datetime
import logging
from quart import Blueprint, request, abort, jsonify
from quart_schema import validate, validate_request
from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)

FINAL_STATES = {'FAILURE', 'SUCCESS', 'CANCELLED', 'CANCELLED_BY_USER', 'UNKNOWN', 'FINISHED'}
PROCESSING_STATE = 'PROCESSING'

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

# Assuming PETSTORE_BASE_URL and FUN_PET_FACTS will be set in app.py or environment

@routes_bp.route("/pets/search", methods=["POST"])
@validate_request
async def pets_search(data):
    """
    POST /pets/search
    Accepts optional filters: type, status
    Creates a 'petsearch' entity; actual search and persistence handled asynchronously in workflow.
    """
    try:
        search_data = {
            "type": data.get("type") if isinstance(data, dict) else getattr(data, "type", None),
            "status": data.get("status") if isinstance(data, dict) else getattr(data, "status", None),
        }
        search_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="petsearch",
            entity_version=None,  # ENTITY_VERSION should be imported or set in app.py
            entity=search_data
        )
        return jsonify({"search_id": search_id, "message": "Pet search request accepted and processing."})

    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to initiate pet search"}), 500


@routes_bp.route("/pets/fun-fact", methods=["POST"])
async def pets_fun_fact():
    import random
    fact = random.choice(FUN_PET_FACTS)
    return jsonify({"fact": fact})


@routes_bp.route("/pets", methods=["GET"])
async def get_pets():
    try:
        pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=None,  # ENTITY_VERSION should be imported or set in app.py
        )
        return jsonify({"pets": pets})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pets"}), 500


@routes_bp.route("/pets/<string:pet_id>", methods=["GET"])
async def get_pet_by_id(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=None,  # ENTITY_VERSION should be imported or set in app.py
            technical_id=pet_id,
        )
        if pet is None:
            return jsonify({"error": f"Pet with id {pet_id} not found."}), 404
        return jsonify(pet)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pet"}), 500