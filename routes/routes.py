from dataclasses import dataclass
from typing import Any
import logging
from datetime import datetime, timezone

import httpx
from quart import Blueprint, jsonify, abort, request
from quart_schema import validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

@dataclass
class ApiUrlPayload:
    api_url: Any  # Accept any JSON-compatible type

@routes_bp.route("/entities", methods=["POST"])
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
        )
    except Exception as e:
        logger.exception(f"Failed to create entity: {e}")
        return jsonify({"error": "Failed to create entity"}), 500

    return jsonify({"id": entity_id}), 201

@routes_bp.route("/entities/<entity_id>", methods=["POST"])
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

@routes_bp.route("/entities/<entity_id>/fetch", methods=["POST"])
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

@routes_bp.route("/entities", methods=["GET"])
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

@routes_bp.route("/entities/<entity_id>", methods=["GET"])
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

@routes_bp.route("/entities/<entity_id>", methods=["DELETE"])
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

@routes_bp.route("/entities", methods=["DELETE"])
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