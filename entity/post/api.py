# Here's the `api.py` file implementing the specified entity post endpoints using the provided template:
# 
# ```python
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION

api_bp_posts = Blueprint('api/posts', __name__)

@api_bp_posts.route('/posts', methods=['POST'])
async def add_post():
    """API endpoint to create a new post with optional image upload."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Add the post entity using the entity service
        post_id = await entity_service.add_item(
            cyoda_token, 'posts', ENTITY_VERSION, data
        )
        return jsonify({"post_id": post_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_posts.route('/posts/<int:post_id>', methods=['GET'])
async def get_post(post_id):
    """API endpoint to retrieve a specific post by its ID."""
    try:
        # Retrieve the post entity using the entity service
        post = await entity_service.get_item(
            cyoda_token, 'posts', ENTITY_VERSION, post_id
        )
        return jsonify(post), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_posts.route('/posts', methods=['GET'])
async def get_all_posts():
    """API endpoint to retrieve all posts."""
    try:
        # Retrieve all posts using the entity service
        posts = await entity_service.get_item(
            cyoda_token, 'posts', ENTITY_VERSION, None
        )
        return jsonify(posts), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ```
# 
# ### Explanation:
# - The `add_post` function handles the creation of a new post. It expects JSON data and uses the `add_item` method from `entity_service`.
# - The `get_post` function retrieves a specific post by its ID using the `get_item` method.
# - The `get_all_posts` function retrieves all posts. Note that the `get_item` method is called with `None` for the ID to signify that we want all posts.
# - Error handling is included to return appropriate error messages and status codes.