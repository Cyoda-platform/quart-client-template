from dataclasses import dataclass
from typing import Any
import logging
from datetime import datetime, timezone

import httpx
from quart import Quart, jsonify, abort
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

@dataclass
class ApiUrlPayload:
    api_url: Any  # Accept any JSON-compatible type

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# Workflow function for 'entity'
async def process_entity(entity: dict) -> None:
    """
    Workflow function applied asynchronously before persisting the entity.
    Modifies entity in-place:
    - Initializes fetch_status
    - Performs external API fetch
    - Updates entity with fetched data, timestamps, and status
    
    Cannot call add/update/delete on 'entity' model here.
    """

    entity.setdefault("fetch_status", "pending")

    api_url = entity.get("api_url")
    if not api_url:
        entity["fetch_status"] = "error: missing api_url"
        entity["fetched_data"] = None
        entity["fetched_at"] = None
        return

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(api_url)
            response.raise_for_status()
            data = response.json()
        entity["fetched_data"] = data
        entity["fetched_at"] = utc_now_iso()
        entity["fetch_status"] = "success"
    except Exception as e:
        logger.exception(f"Error fetching external API for entity inside workflow: {e}")
        entity["fetched_data"] = None
        entity["fetched_at"] = None
        entity["fetch_status"] = f"error: {str(e)}"

@app.route("/entities", methods=["POST"])
@validate_request(ApiUrlPayload)
async def create_entity(data: ApiUrlPayload):
    api_url = data.api_url
    if api_url is None:
        return jsonify({"error": "api_url field is required"}), 400

    entity_dict = {
        "api_url": api_url,
    }

    try:
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            entity=entity_dict,
            workflow=process_entity,
        )
    except Exception as e:
        logger.exception(f"Failed to create entity: {e}")
        return jsonify({"error": "Failed to create entity"}), 500

    return jsonify({"id": entity_id}), 201

@app.route("/entities/<entity_id>", methods=["POST"])
@validate_request(ApiUrlPayload)
async def update_entity(entity_id, data: ApiUrlPayload):
    try:
        entity = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            technical_id=entity_id,
        )
    except Exception as e:
        logger.exception(f"Failed to retrieve entity {entity_id} for update: {e}")
        abort(500, description="Internal Server Error")

    if not entity:
        abort(404, description="Entity not found")

    api_url = data.api_url
    if api_url is None:
        return jsonify({"error": "api_url field is required"}), 400

    entity["api_url"] = api_url

    try:
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            entity=entity,
            technical_id=entity_id,
            meta={},
            workflow=process_entity,
        )
    except Exception as e:
        logger.exception(f"Failed to update entity {entity_id}: {e}")
        return jsonify({"error": "Failed to update entity"}), 500

    return jsonify(entity)

@app.route("/entities/<entity_id>/fetch", methods=["POST"])
async def manual_fetch(entity_id):
    try:
        entity = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            technical_id=entity_id,
        )
    except Exception as e:
        logger.exception(f"Failed to retrieve entity {entity_id} for manual fetch: {e}")
        abort(500, description="Internal Server Error")

    if not entity:
        abort(404, description="Entity not found")

    try:
        # Trigger workflow by updating entity without changes
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            entity=entity,
            technical_id=entity_id,
            meta={},
            workflow=process_entity,
        )
    except Exception as e:
        logger.exception(f"Failed to trigger manual fetch workflow for entity {entity_id}: {e}")
        return jsonify({"error": "Failed to fetch entity data"}), 500

    try:
        updated_entity = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            technical_id=entity_id,
        )
    except Exception as e:
        logger.exception(f"Failed to retrieve entity {entity_id} after fetch: {e}")
        abort(500, description="Internal Server Error")

    return jsonify({
        "id": entity_id,
        "fetched_data": updated_entity.get("fetched_data"),
        "fetched_at": updated_entity.get("fetched_at"),
        "fetch_status": updated_entity.get("fetch_status"),
    })

@app.route("/entities", methods=["GET"])
async def get_all_entities():
    try:
        entities = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.exception(f"Failed to retrieve all entities: {e}")
        return jsonify({"error": "Failed to retrieve entities"}), 500

    return jsonify(entities)

@app.route("/entities/<entity_id>", methods=["GET"])
async def get_entity_by_id(entity_id):
    try:
        entity = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            technical_id=entity_id,
        )
    except Exception as e:
        logger.exception(f"Failed to retrieve entity {entity_id}: {e}")
        abort(500, description="Internal Server Error")

    if not entity:
        abort(404, description="Entity not found")

    return jsonify(entity)

@app.route("/entities/<entity_id>", methods=["DELETE"])
async def delete_entity(entity_id):
    try:
        entity = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            technical_id=entity_id,
        )
    except Exception as e:
        logger.exception(f"Failed to retrieve entity {entity_id} for deletion: {e}")
        abort(500, description="Internal Server Error")

    if not entity:
        abort(404, description="Entity not found")

    try:
        await entity_service.delete_item(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
            technical_id=entity_id,
            meta={},
        )
    except Exception as e:
        logger.exception(f"Failed to delete entity {entity_id}: {e}")
        return jsonify({"error": "Failed to delete entity"}), 500

    return "", 204

@app.route("/entities", methods=["DELETE"])
async def delete_all_entities():
    try:
        entities = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="entity",
            entity_version=ENTITY_VERSION,
        )
        if entities:
            for entity in entities:
                try:
                    await entity_service.delete_item(
                        token=cyoda_auth_service,
                        entity_model="entity",
                        entity_version=ENTITY_VERSION,
                        technical_id=entity.get("id"),
                        meta={},
                    )
                except Exception as e:
                    logger.exception(f"Failed to delete entity {entity.get('id')}: {e}")
    except Exception as e:
        logger.exception(f"Failed to retrieve entities for bulk deletion: {e}")
        return jsonify({"error": "Failed to delete entities"}), 500

    return "", 204

if __name__ == '__main__':
    import sys
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)