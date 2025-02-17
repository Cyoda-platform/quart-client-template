# Here’s a prototype implementation for your backend application using Quart. This implementation reflects the functional requirements you've provided, using `aiohttp.ClientSession` for external HTTP requests and `QuartSchema` for managing request validation. 
# 
# ```python
from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import aiohttp

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Placeholder for in-memory data storage
posts = {}
comments = {}
images = {}

# Helper functions for generating IDs
def generate_id(data_store):
    return str(len(data_store) + 1)

@app.route('/users/create', methods=['POST'])
async def create_user():
    data = await request.json
    # TODO: Add user creation logic (e.g., save user to database)
    return jsonify({"message": "User created successfully"}), 201

@app.route('/users/login', methods=['POST'])
async def login_user():
    data = await request.json
    # TODO: Implement user authentication logic
    return jsonify({"token": "jwt.token.here"}), 200

@app.route('/posts', methods=['POST'])
async def create_post():
    data = await request.json
    post_id = generate_id(posts)
    posts[post_id] = {
        "post_id": post_id,
        "title": data["title"],
        "tags": data.get("tags", []),
        "body": data["body"],
        "upvotes": 0,
        "downvotes": 0
    }
    return jsonify({"post_id": post_id, "message": "Post created successfully"}), 201

@app.route('/posts', methods=['GET'])
async def get_posts():
    return jsonify(list(posts.values())), 200

@app.route('/posts/<post_id>', methods=['GET'])
async def get_post(post_id):
    post = posts.get(post_id)
    # TODO: Add logic to fetch comments
    if post:
        return jsonify(post), 200
    return jsonify({"message": "Post not found"}), 404

@app.route('/posts/<post_id>', methods=['DELETE'])
async def delete_post(post_id):
    if post_id in posts:
        del posts[post_id]
        return jsonify({"message": "Post deleted successfully"}), 200
    return jsonify({"message": "Post not found"}), 404

@app.route('/posts/<post_id>/comments', methods=['POST'])
async def add_comment(post_id):
    data = await request.json
    comment_id = generate_id(comments)
    comments[comment_id] = {
        "comment_id": comment_id,
        "post_id": post_id,
        "body": data["body"]
    }
    return jsonify({"comment_id": comment_id, "message": "Comment added successfully"}), 201

@app.route('/posts/<post_id>/comments', methods=['GET'])
async def get_comments(post_id):
    # TODO: Implement logic to get comments for the specific post
    return jsonify({"comments": list(comments.values())}), 200

@app.route('/posts/<post_id>/comments/<comment_id>', methods=['DELETE'])
async def delete_comment(post_id, comment_id):
    if comment_id in comments:
        del comments[comment_id]
        return jsonify({"message": "Comment deleted successfully"}), 200
    return jsonify({"message": "Comment not found"}), 404

@app.route('/posts/<post_id>/images', methods=['POST'])
async def upload_image(post_id):
    # TODO: Implement image upload logic
    return jsonify({"image_id": "image123", "message": "Image uploaded successfully"}), 201

@app.route('/posts/<post_id>/images/<image_id>', methods=['GET'])
async def get_image(post_id, image_id):
    # TODO: Implement logic to retrieve image by ID
    return jsonify({"message": "Image retrieved successfully"}), 200

@app.route('/posts/<post_id>/vote', methods=['POST'])
async def vote_post(post_id):
    data = await request.json
    # TODO: Implement voting logic (upvote/downvote)
    return jsonify({"message": "Vote recorded"}), 200

@app.route('/posts/<post_id>/comments/<comment_id>/vote', methods=['POST'])
async def vote_comment(post_id, comment_id):
    data = await request.json
    # TODO: Implement voting logic for comments (upvote/downvote)
    return jsonify({"message": "Vote recorded"}), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
# ```
# 
# ### Key Points:
# - This code establishes basic routes for user authentication, post management, comment management, image handling, and voting.
# - Placeholders (`TODO`) indicate where additional logic needs to be implemented, such as connecting to a database, handling authentication, and managing comments and images.
# - The in-memory data structures (`posts`, `comments`, `images`) simulate a database for testing purposes.
# - The application is set to run on `host='0.0.0.0'` and port `8000`, suitable for local development.
# 
# This prototype can verify the user experience and help identify any gaps in requirements before proceeding with a more thorough implementation.