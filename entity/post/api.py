# Here’s the `api.py` file implementing the post entity endpoints as per your request, following the provided template:
# 
# ```python
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION

api_bp_post = Blueprint('api/post', __name__)

@api_bp_post.route('/posts', methods=['POST'])
async def add_post():
    """API endpoint to create a new post."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Add the post entity using the entity service
        post_id = await entity_service.add_item(
            cyoda_token, 'post', ENTITY_VERSION, data
        )
        return jsonify({"post_id": post_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_post.route('/posts', methods=['GET'])
async def get_posts():
    """API endpoint to get a list of posts."""
    try:
        # This would typically involve a method to get all posts, 
        # but since we only have get_item, we will return a placeholder.
        # Assuming entity_service has a method to get all items.
        posts = await entity_service.get_item(
            cyoda_token, 'post', ENTITY_VERSION, None  # Placeholder for getting all posts
        )
        return jsonify({"posts": posts}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_post.route('/posts/<int:post_id>', methods=['GET'])
async def get_post(post_id):
    """API endpoint to get a specific post."""
    try:
        # Get the specific post entity using the entity service
        post_data = await entity_service.get_item(
            cyoda_token, 'post', ENTITY_VERSION, post_id
        )
        return jsonify({"post_data": post_data}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ```
# 
# ### Explanation:
# - The `add_post` function handles the creation of a new post by accepting a JSON payload and using the `add_item` method from `entity_service`.
# - The `get_posts` function is designed to retrieve a list of posts. Since the `entity_service` only has `get_item`, this function assumes a placeholder for retrieving all posts.
# - The `get_post` function retrieves a specific post based on the provided `post_id` using the `get_item` method.
# - Each function handles exceptions and returns appropriate HTTP status codes and messages.