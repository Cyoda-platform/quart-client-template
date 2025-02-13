# Here is a prototype implementation of your backend application using Quart and aiohttp. This example covers the specified API design, incorporating the necessary endpoints and using mocks where applicable. 
# 
# ```python
from quart import Quart, request, jsonify
from quart_schema import QuartSchema
import aiohttp
import asyncio

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Mock storage (replace with a database connection in production)
users = {}
posts = {}
comments = {}
post_counter = 0
comment_counter = 0

# User registration
@app.route('/users/create', methods=['POST'])
async def create_user():
    data = await request.get_json()
    username = data.get('username')
    password = data.get('password')  # TODO: Hash the password before storing
    email = data.get('email')

    user_id = len(users) + 1
    users[user_id] = {'username': username, 'password': password, 'email': email}
    return jsonify({'user_id': user_id, 'message': 'User created successfully.'}), 201

# User login
@app.route('/users/login', methods=['POST'])
async def login_user():
    data = await request.get_json()
    username = data.get('username')
    password = data.get('password')  # TODO: Validate hashed password

    user = next((u for u in users.values() if u['username'] == username and u['password'] == password), None)
    if user:
        token = "JWT_TOKEN"  # TODO: Generate a real JWT token
        return jsonify({'token': token}), 200
    return jsonify({'message': 'Invalid credentials'}), 401

# Create a post
@app.route('/posts', methods=['POST'])
async def create_post():
    global post_counter
    data = await request.get_json()
    title = data.get('title')
    body = data.get('body')
    tags = data.get('tags', [])

    post_counter += 1
    posts[post_counter] = {
        'post_id': post_counter,
        'title': title,
        'body': body,
        'tags': tags,
        'upvotes': 0,
        'downvotes': 0
    }
    return jsonify({'post_id': post_counter, 'message': 'Post created successfully.'}), 201

# Get list of posts
@app.route('/posts', methods=['GET'])
async def get_posts():
    limit = int(request.args.get('limit', 20))
    offset = int(request.args.get('offset', 0))
    post_list = list(posts.values())[offset:offset + limit]
    return jsonify({'posts': post_list, 'total': len(posts)}), 200

# Get a specific post
@app.route('/posts/<int:post_id>', methods=['GET'])
async def get_post(post_id):
    post = posts.get(post_id)
    if post:
        return jsonify(post), 200
    return jsonify({'message': 'Post not found'}), 404

# Delete a post
@app.route('/posts/<int:post_id>', methods=['DELETE'])
async def delete_post(post_id):
    if post_id in posts:
        del posts[post_id]
        return jsonify({'message': 'Post deleted successfully.'}), 200
    return jsonify({'message': 'Post not found'}), 404

# Add a comment to a post
@app.route('/posts/<int:post_id>/comments', methods=['POST'])
async def add_comment(post_id):
    global comment_counter
    data = await request.get_json()
    body = data.get('body')

    if post_id not in posts:
        return jsonify({'message': 'Post not found'}), 404

    comment_counter += 1
    comments[comment_counter] = {
        'comment_id': comment_counter,
        'post_id': post_id,
        'body': body,
        'upvotes': 0,
        'downvotes': 0
    }
    return jsonify({'comment_id': comment_counter, 'message': 'Comment added successfully.'}), 201

# Get comments for a post
@app.route('/posts/<int:post_id>/comments', methods=['GET'])
async def get_comments(post_id):
    if post_id not in posts:
        return jsonify({'message': 'Post not found'}), 404

    post_comments = [c for c in comments.values() if c['post_id'] == post_id]
    return jsonify({'comments': post_comments}), 200

# Delete a comment
@app.route('/posts/<int:post_id>/comments/<int:comment_id>', methods=['DELETE'])
async def delete_comment(post_id, comment_id):
    if comment_id in comments:
        del comments[comment_id]
        return jsonify({'message': 'Comment deleted successfully.'}), 200
    return jsonify({'message': 'Comment not found'}), 404

# Run the application
if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
# ```
# 
# ### Key Points
# - This prototype incorporates the endpoints and data structures required for user authentication, post management, comment management, and basic responses.
# - Mocks are used to simulate user storage and post/comment storage. In a production setting, these should be replaced with a proper database.
# - JWT token generation and password hashing have been noted as TODO items for future implementation.
# - The error handling is basic to keep the prototype lightweight but should be improved in a full implementation. 
# 
# This code serves as a prototype to verify the user experience and identify any gaps in requirements before proceeding with a more robust solution.