from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
import uuid
import asyncio

api_bp_cat_fact = Blueprint('api/cat_fact', __name__)

ENTITY_MODEL = 'cat_fact'

@api_bp_cat_fact.route('/cat-facts', methods=['GET'])
async def get_cat_facts():
    """Retrieve cat_fact information."""
    try:
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
