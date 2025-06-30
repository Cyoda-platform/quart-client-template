import logging
import datetime
from quart import Quart, request, jsonify
from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)

entity_name = "prototype"  # entity name in underscore lowercase


async def enrich_prototype(entity):
    # Placeholder for async enrichment logic, e.g. fetching external data
    # Simulated with pass, replace with actual async code if needed
    pass


async def log_prototype_creation(entity):
    # Add a supplementary entity/log for audit purposes (different entity_model)
    log_entity = {
        "prototype_id": entity.get("id"),
        "event": "created",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model='prototype_log',  # different entity model
            entity_version=ENTITY_VERSION,
            entity=log_entity,
            workflow=None  # no workflow for log entity
        )
    except Exception:
        logger.exception("Failed to log prototype creation")


async def process_prototype(entity):
    # Add processed timestamp
    entity['processed_at'] = datetime.datetime.utcnow().isoformat()

    # Await enrichment logic
    await enrich_prototype(entity)

    # Log creation event asynchronously (supplementary entity)
    await log_prototype_creation(entity)

    # Additional entity state changes can be made here if needed

    return entity


@app.route('/prototypes', methods=['POST'])
async def create_prototype():
    try:
        data = await request.get_json()
        if not data or not isinstance(data, dict):
            return jsonify({"error": "Invalid input data"}), 400

        # Add item with workflow handling async business logic pre-persistence
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({"id": str(id)}), 201
    except Exception:
        logger.exception("Failed to create prototype")
        return jsonify({"error": "Failed to create prototype"}), 500


@app.route('/prototypes/<string:id>', methods=['GET'])
async def get_prototype(id):
    try:
        item = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            technical_id=id
        )
        if item is None:
            return jsonify({"error": "Prototype not found"}), 404
        return jsonify(item), 200
    except Exception:
        logger.exception("Failed to get prototype")
        return jsonify({"error": "Failed to get prototype"}), 500


@app.route('/prototypes', methods=['GET'])
async def get_prototypes():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION
        )
        return jsonify(items), 200
    except Exception:
        logger.exception("Failed to get prototypes")
        return jsonify({"error": "Failed to get prototypes"}), 500


@app.route('/prototypes/<string:id>', methods=['PUT'])
async def update_prototype(id):
    try:
        data = await request.get_json()
        if not data or not isinstance(data, dict):
            return jsonify({"error": "Invalid input data"}), 400

        # If needed, create a similar workflow for update operations
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=data,
            technical_id=id,
            meta={}
        )
        return jsonify({"message": "Prototype updated"}), 200
    except Exception:
        logger.exception("Failed to update prototype")
        return jsonify({"error": "Failed to update prototype"}), 500


@app.route('/prototypes/<string:id>', methods=['DELETE'])
async def delete_prototype(id):
    try:
        await entity_service.delete_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            technical_id=id,
            meta={}
        )
        return jsonify({"message": "Prototype deleted"}), 200
    except Exception:
        logger.exception("Failed to delete prototype")
        return jsonify({"error": "Failed to delete prototype"}), 500


@app.route('/prototypes/search', methods=['POST'])
async def search_prototypes():
    try:
        condition = await request.get_json()
        if not condition or not isinstance(condition, dict):
            return jsonify({"error": "Invalid search condition"}), 400

        items = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        return jsonify(items), 200
    except Exception:
        logger.exception("Failed to search prototypes")
        return jsonify({"error": "Failed to search prototypes"}), 500
