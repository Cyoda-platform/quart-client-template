import logging
from quart import Quart, request, jsonify
from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)

entity_name = "entity_name"  # replace with actual entity name in underscore lowercase


@app.route(f"/{entity_name}/", methods=["POST"])
async def create_entity():
    try:
        data = await request.get_json()
        # Validate data here if needed (preserve existing validation logic)
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({"id": str(id)}), 201
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to create entity"}), 500


@app.route(f"/{entity_name}/<string:entity_id>", methods=["GET"])
async def get_entity(entity_id):
    try:
        item = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            technical_id=entity_id
        )
        if item is None:
            return jsonify({"error": "Entity not found"}), 404
        return jsonify(item), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve entity"}), 500


@app.route(f"/{entity_name}/", methods=["GET"])
async def get_entities():
    try:
        # Check if there is a query param for condition
        condition = request.args.get("condition")
        if condition:
            # Conditions expected to be JSON string; parse it
            import json
            try:
                condition_obj = json.loads(condition)
            except Exception:
                return jsonify({"error": "Invalid condition JSON"}), 400

            items = await entity_service.get_items_by_condition(
                token=cyoda_auth_service,
                entity_model=entity_name,
                entity_version=ENTITY_VERSION,
                condition=condition_obj
            )
        else:
            items = await entity_service.get_items(
                token=cyoda_auth_service,
                entity_model=entity_name,
                entity_version=ENTITY_VERSION
            )
        return jsonify(items), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve entities"}), 500


@app.route(f"/{entity_name}/<string:entity_id>", methods=["PUT"])
async def update_entity(entity_id):
    try:
        data = await request.get_json()
        # Validate data if needed
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=data,
            technical_id=entity_id,
            meta={}
        )
        return jsonify({"message": "Entity updated"}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to update entity"}), 500


@app.route(f"/{entity_name}/<string:entity_id>", methods=["DELETE"])
async def delete_entity(entity_id):
    try:
        await entity_service.delete_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            technical_id=entity_id,
            meta={}
        )
        return jsonify({"message": "Entity deleted"}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to delete entity"}), 500