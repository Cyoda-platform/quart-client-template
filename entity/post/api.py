from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
import uuid
import asyncio

api_bp_post = Blueprint('api/post', __name__)

ENTITY_MODEL = 'post'

@api_bp_post.route('/posts', methods=['GET'])
async def get_posts():
    """Retrieve post information."""
    try:
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_post.route('/posts/<int:post_id>', methods=['GET'])
async def get_int:post_id(int:post_id):
    """Retrieve post information."""
    try:
        data = await entity_service.get_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            technical_id=int:post_id
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_post.route('/posts/<int:post_id>', methods=['GET'])
async def get_int:post_id(int:post_id):
    """Retrieve post information."""
    try:
        data = await entity_service.get_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            technical_id=int:post_id
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_post.route('/posts/<int:post_id>/comments', methods=['GET'])
async def get_int:post_id(int:post_id):
    """Retrieve post information."""
    try:
        data = await entity_service.get_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            technical_id=int:post_id
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_post.route('/posts/<int:post_id>/comments/<int:comment_id>', methods=['GET'])
async def get_int:post_id(int:post_id, int:comment_id):
    """Retrieve post information."""
    try:
        data = await entity_service.get_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            technical_id=int:post_id
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_post.route('/posts/<int:post_id>/images/<int:image_id>', methods=['GET'])
async def get_int:post_id(int:post_id, int:image_id):
    """Retrieve post information."""
    try:
        data = await entity_service.get_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            technical_id=int:post_id
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
