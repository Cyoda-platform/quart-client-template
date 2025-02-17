from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
import uuid
import asyncio

api_bp_posts = Blueprint('api/posts', __name__)

ENTITY_MODEL = 'posts'

@api_bp_posts.route('/posts', methods=['POST'])
async def add_posts():
    """Create a new posts."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        posts_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({'posts_id': posts_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_posts.route('/posts/<int:post_id>/comments', methods=['POST'])
async def add_posts(int:post_id):
    """Create a new posts."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        posts_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({'posts_id': posts_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_posts.route('/posts/<int:post_id>/images', methods=['POST'])
async def add_posts(int:post_id):
    """Create a new posts."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        posts_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({'posts_id': posts_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_posts.route('/posts/<int:post_id>/vote', methods=['POST'])
async def add_posts(int:post_id):
    """Create a new posts."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        posts_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({'posts_id': posts_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_posts.route('/posts/<int:post_id>/comments/<int:comment_id>/vote', methods=['POST'])
async def add_posts(int:post_id, int:comment_id):
    """Create a new posts."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        posts_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
            entity=data
        )
        return jsonify({'posts_id': posts_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_posts.route('/posts', methods=['GET'])
async def get_postss():
    """Retrieve posts by identifier."""
    try:
        data = await entity_service.get_items(
            token=cyoda_token,
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION
        )
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_posts.route('/posts/<int:post_id>', methods=['GET'])
async def get_int:post_id(int:post_id):
    """Retrieve posts by identifier."""
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

@api_bp_posts.route('/posts/<int:post_id>/comments', methods=['GET'])
async def get_int:post_id(int:post_id):
    """Retrieve posts by identifier."""
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

@api_bp_posts.route('/posts/<int:post_id>/images/<int:image_id>', methods=['GET'])
async def get_int:post_id(int:post_id, int:image_id):
    """Retrieve posts by identifier."""
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
