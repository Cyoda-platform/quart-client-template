# Here’s the `api.py` file implementing the comment entity endpoints as per your request, following the provided template:
# 
# ```python
from quart import Blueprint, request, jsonify
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION

api_bp_comment = Blueprint('api/comment', __name__)

@api_bp_comment.route('/posts/<int:post_id>/comments', methods=['POST'])
async def add_comment(post_id):
    """API endpoint to add a comment to a specific post."""
    data = await request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Add the comment entity using the entity service
        comment_id = await entity_service.add_item(
            cyoda_token, 'comment', ENTITY_VERSION, {**data, 'post_id': post_id}
        )
        return jsonify({"comment_id": comment_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp_comment.route('/posts/<int:post_id>/comments', methods=['GET'])
async def get_comments(post_id):
    """API endpoint to get comments for a specific post."""
    try:
        # Get comments for the specific post using the entity service
        comments = await entity_service.get_item(
            cyoda_token, 'comment', ENTITY_VERSION, post_id  # Assuming this retrieves comments for the post
        )
        return jsonify({"comments": comments}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ```
# 
# ### Explanation:
# - The `add_comment` function handles adding a comment to a specific post by accepting a JSON payload and using the `add_item` method from `entity_service`. The `post_id` is included in the data to associate the comment with the correct post.
# - The `get_comments` function retrieves comments for a specific post using the `get_item` method. It assumes that the `entity_service` can retrieve comments based on the `post_id`.
# - Both functions handle exceptions and return appropriate HTTP status codes and messages.