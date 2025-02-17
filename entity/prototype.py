# Below is a simple prototype implementation of your backend application using the Quart framework. It incorporates the specified API design and uses `aiohttp` for HTTP requests. Mocks and placeholders are added where necessary, indicated by TODO comments.
# 
# ```python
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema for request validation

# In-memory storage for demonstration purposes
posts = {}
comments = {}
images = {}
user_tokens = {}
post_counter = 1  # Simulate post IDs
comment_counter = 1  # Simulate comment IDs
image_counter = 1  # Simulate image IDs

@app.route('/users/create', methods=['POST'])
async def create_user():
    data = await request.get_json()
    # TODO: Implement user creation logic (e.g., save to database)
    return jsonify({"message": "User created successfully", "user_id": "1"})

@app.route('/users/login', methods=['POST'])
async def login():
    data = await request.get_json()
    # TODO: Implement user authentication and JWT token generation
    return jsonify({"token": "JWT_TOKEN"})

@app.route('/posts', methods=['POST'])
async def create_post():
    global post_counter
    data = await request.get_json()
    post_id = post_counter
    posts[post_id] = {
        "post_id": post_id,
        "title": data["title"],
        "topics": data["topics"],
        "body": data["body"],
        "upvotes": 0,
        "downvotes": 0
    }
    post_counter += 1
    return jsonify({"post_id": post_id, "message": "Post created successfully"})

@app.route('/posts', methods=['GET'])
async def get_posts():
    limit = int(request.args.get('limit', 20))
    offset = int(request.args.get('offset', 0))
    response_posts = list(posts.values())[offset:offset + limit]
    return jsonify({"posts": response_posts, "total": len(posts)})

@app.route('/posts/<int:post_id>', methods=['GET'])
async def get_post(post_id):
    post = posts.get(post_id)
    if post:
        return jsonify(post)
    return jsonify({"error": "Post not found"}), 404

@app.route('/posts/<int:post_id>', methods=['DELETE'])
async def delete_post(post_id):
    if post_id in posts:
        del posts[post_id]
        return jsonify({"message": "Post deleted successfully"})
    return jsonify({"error": "Post not found"}), 404

@app.route('/posts/<int:post_id>/comments', methods=['POST'])
async def add_comment(post_id):
    global comment_counter
    data = await request.get_json()
    if post_id not in posts:
        return jsonify({"error": "Post not found"}), 404
    
    comment_id = comment_counter
    comments[comment_id] = {
        "comment_id": comment_id,
        "body": data["body"],
        "post_id": post_id,
        "upvotes": 0,
        "downvotes": 0
    }
    comment_counter += 1
    return jsonify({"comment_id": comment_id, "message": "Comment added successfully"})

@app.route('/posts/<int:post_id>/comments', methods=['GET'])
async def get_comments(post_id):
    if post_id not in posts:
        return jsonify({"error": "Post not found"}), 404
    
    response_comments = [c for c in comments.values() if c['post_id'] == post_id]
    return jsonify({"comments": response_comments})

@app.route('/posts/<int:post_id>/comments/<int:comment_id>', methods=['DELETE'])
async def delete_comment(post_id, comment_id):
    if comment_id in comments:
        del comments[comment_id]
        return jsonify({"message": "Comment deleted successfully"})
    return jsonify({"error": "Comment not found"}), 404

@app.route('/posts/<int:post_id>/images', methods=['POST'])
async def upload_image(post_id):
    # TODO: Implement image upload logic (e.g., save to storage)
    return jsonify({"image_id": image_counter, "message": "Image uploaded successfully"})

@app.route('/posts/<int:post_id>/images/<int:image_id>', methods=['GET'])
async def get_image(post_id, image_id):
    # TODO: Implement image retrieval logic (e.g., from storage)
    return jsonify({"error": "Image not found"}), 404

@app.route('/posts/<int:post_id>/vote', methods=['POST'])
async def vote_post(post_id):
    data = await request.get_json()
    # TODO: Add voting logic (upvotes/downvotes)
    return jsonify({"message": "Vote recorded"})

@app.route('/posts/<int:post_id>/comments/<int:comment_id>/vote', methods=['POST'])
async def vote_comment(post_id, comment_id):
    data = await request.get_json()
    # TODO: Add voting logic for comments (upvotes/downvotes)
    return jsonify({"message": "Vote recorded"})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
# ```
# 
# ### Notes:
# - The code snippet represents a basic prototype of the specified functionality.
# - Mocks and placeholders have been included where implementations are needed (e.g., for user authentication, image uploads, and voting logic).
# - The in-memory storage (dictionaries) is used for demonstration purposes; consider using a database for production.
# - Ensure to implement the TODO sections based on your application's requirements in future iterations.
# 
# Feel free to test this prototype and identify any gaps or additional features that may be required!