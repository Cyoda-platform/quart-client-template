import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
import httpx

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Dataclass definitions for request validation
@dataclass
class BookData:
    title: str
    description: str
    authorId: int

@dataclass
class AuthorData:
    name: str
    biography: str

@dataclass
class UserData:
    name: str
    email: str

@dataclass
class TaskData:
    title: str
    description: str
    status: str

@dataclass
class AuthenticationData:
    username: str
    password: str

# Base URL for the external FakeRest API
FAKER_API_URL = "https://fakerestapi.azurewebsites.net/api/v1"

# In-memory persistence (local cache)
books_cache = {}
authors_cache = {}
users_cache = {}
tasks_cache = {}
activities_cache = []  # List of activities

# Global counters for ids (mock persistence IDs)
next_book_id = 1
next_author_id = 1
next_user_id = 1
next_task_id = 1

# Utility function for processing tasks in background (example pattern)
async def process_entity(entity_job, data):
    try:
        # TODO: Implement actual processing logic here
        await asyncio.sleep(1)
        entity_job["status"] = "completed"
        logger.info(f"Finished processing entity: {data}")
    except Exception as e:
        logger.exception(e)
        entity_job["status"] = "failed"

# POST endpoints: route decorator must go first, then validation (@validate_request) workaround for quart-schema
@app.route('/books', methods=['POST'])
@validate_request(BookData)  # Works around the quart-schema ordering issue for POST requests
async def add_book(data: BookData):
    global next_book_id
    try:
        # Simulate external API call to create a book
        async with httpx.AsyncClient() as client:
            external_response = await client.post(f"{FAKER_API_URL}/Books", json=data.__dict__)
            external_response.raise_for_status()  # Raise error if bad response
            external_book = external_response.json()
        # Use local cache to simulate persistence
        book = {
            "id": next_book_id,
            "title": data.title,
            "description": data.description,
            "authorId": data.authorId
        }
        books_cache[next_book_id] = book
        next_book_id += 1

        # Fire and forget background processing
        job = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
        asyncio.create_task(process_entity(job, book))

        return jsonify(book)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add book"}), 500

@app.route('/books', methods=['GET'])
async def get_books():
    # Return local cache of books
    return jsonify(list(books_cache.values()))

@app.route('/books/<int:book_id>', methods=['POST'])
@validate_request(BookData)  # Works around the quart-schema ordering issue for POST requests
async def update_book(book_id: int, data: BookData):
    try:
        if book_id not in books_cache:
            return jsonify({"error": "Book not found"}), 404

        # Simulate external API call to update a book
        async with httpx.AsyncClient() as client:
            external_response = await client.post(f"{FAKER_API_URL}/Books/{book_id}", json=data.__dict__)
            external_response.raise_for_status()
            external_book = external_response.json()

        # Update local cache
        book = books_cache[book_id]
        book.update({
            "title": data.title,
            "description": data.description,
            "authorId": data.authorId
        })
        # Fire and forget background task
        job = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
        asyncio.create_task(process_entity(job, book))
        return jsonify(book)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to update book"}), 500

@app.route('/books/<int:book_id>', methods=['DELETE'])
async def delete_book(book_id: int):
    try:
        if book_id not in books_cache:
            return jsonify({"error": "Book not found"}), 404

        # Simulate external API delete call (assuming DELETE is permitted)
        async with httpx.AsyncClient() as client:
            external_response = await client.delete(f"{FAKER_API_URL}/Books/{book_id}")
            external_response.raise_for_status()

        # Remove from local cache
        del books_cache[book_id]
        return jsonify({"message": "Book deleted successfully"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to delete book"}), 500

@app.route('/authors', methods=['POST'])
@validate_request(AuthorData)  # Works around the quart-schema ordering issue for POST requests
async def add_author(data: AuthorData):
    global next_author_id
    try:
        async with httpx.AsyncClient() as client:
            external_response = await client.post(f"{FAKER_API_URL}/Authors", json=data.__dict__)
            external_response.raise_for_status()
            external_author = external_response.json()

        author = {
            "id": next_author_id,
            "name": data.name,
            "biography": data.biography
        }
        authors_cache[next_author_id] = author
        next_author_id += 1

        # Background task example
        job = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
        asyncio.create_task(process_entity(job, author))
        return jsonify(author)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add author"}), 500

@app.route('/authors', methods=['GET'])
async def get_authors():
    return jsonify(list(authors_cache.values()))

@app.route('/authors/<int:author_id>', methods=['POST'])
@validate_request(AuthorData)  # Works around the quart-schema ordering issue for POST requests
async def update_author(author_id: int, data: AuthorData):
    try:
        if author_id not in authors_cache:
            return jsonify({"error": "Author not found"}), 404

        async with httpx.AsyncClient() as client:
            external_response = await client.post(f"{FAKER_API_URL}/Authors/{author_id}", json=data.__dict__)
            external_response.raise_for_status()
            external_author = external_response.json()

        author = authors_cache[author_id]
        author.update({
            "name": data.name,
            "biography": data.biography
        })
        job = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
        asyncio.create_task(process_entity(job, author))
        return jsonify(author)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to update author"}), 500

@app.route('/authors/<int:author_id>', methods=['DELETE'])
async def delete_author(author_id: int):
    try:
        if author_id not in authors_cache:
            return jsonify({"error": "Author not found"}), 404

        async with httpx.AsyncClient() as client:
            external_response = await client.delete(f"{FAKER_API_URL}/Authors/{author_id}")
            external_response.raise_for_status()

        del authors_cache[author_id]
        return jsonify({"message": "Author deleted successfully"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to delete author"}), 500

@app.route('/users', methods=['POST'])
@validate_request(UserData)  # Works around the quart-schema ordering issue for POST requests
async def add_user(data: UserData):
    global next_user_id
    try:
        async with httpx.AsyncClient() as client:
            external_response = await client.post(f"{FAKER_API_URL}/Users", json=data.__dict__)
            external_response.raise_for_status()
            external_user = external_response.json()

        user = {
            "id": next_user_id,
            "name": data.name,
            "email": data.email
        }
        users_cache[next_user_id] = user
        next_user_id += 1

        job = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
        asyncio.create_task(process_entity(job, user))
        return jsonify(user)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add user"}), 500

@app.route('/users', methods=['GET'])
async def get_users():
    return jsonify(list(users_cache.values()))

@app.route('/users/<int:user_id>', methods=['POST'])
@validate_request(UserData)  # Works around the quart-schema ordering issue for POST requests
async def update_user(user_id: int, data: UserData):
    try:
        if user_id not in users_cache:
            return jsonify({"error": "User not found"}), 404

        async with httpx.AsyncClient() as client:
            external_response = await client.post(f"{FAKER_API_URL}/Users/{user_id}", json=data.__dict__)
            external_response.raise_for_status()
            external_user = external_response.json()

        user = users_cache[user_id]
        user.update({
            "name": data.name,
            "email": data.email
        })
        job = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
        asyncio.create_task(process_entity(job, user))
        return jsonify(user)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to update user"}), 500

@app.route('/users/<int:user_id>', methods=['DELETE'])
async def delete_user(user_id: int):
    try:
        if user_id not in users_cache:
            return jsonify({"error": "User not found"}), 404

        async with httpx.AsyncClient() as client:
            external_response = await client.delete(f"{FAKER_API_URL}/Users/{user_id}")
            external_response.raise_for_status()

        del users_cache[user_id]
        return jsonify({"message": "User deleted successfully"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to delete user"}), 500

@app.route('/tasks', methods=['POST'])
@validate_request(TaskData)  # Works around the quart-schema ordering issue for POST requests
async def add_task(data: TaskData):
    global next_task_id
    try:
        async with httpx.AsyncClient() as client:
            external_response = await client.post(f"{FAKER_API_URL}/Tasks", json=data.__dict__)
            external_response.raise_for_status()
            external_task = external_response.json()

        task = {
            "id": next_task_id,
            "title": data.title,
            "description": data.description,
            "status": data.status
        }
        tasks_cache[next_task_id] = task
        next_task_id += 1

        job = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
        asyncio.create_task(process_entity(job, task))
        return jsonify(task)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add task"}), 500

@app.route('/tasks', methods=['GET'])
async def get_tasks():
    return jsonify(list(tasks_cache.values()))

@app.route('/tasks/<int:task_id>', methods=['POST'])
@validate_request(TaskData)  # Works around the quart-schema ordering issue for POST requests
async def update_task(task_id: int, data: TaskData):
    try:
        if task_id not in tasks_cache:
            return jsonify({"error": "Task not found"}), 404

        async with httpx.AsyncClient() as client:
            external_response = await client.post(f"{FAKER_API_URL}/Tasks/{task_id}", json=data.__dict__)
            external_response.raise_for_status()
            external_task = external_response.json()

        task = tasks_cache[task_id]
        task.update({
            "title": data.title,
            "description": data.description,
            "status": data.status
        })
        job = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
        asyncio.create_task(process_entity(job, task))
        return jsonify(task)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to update task"}), 500

@app.route('/tasks/<int:task_id>', methods=['DELETE'])
async def delete_task(task_id: int):
    try:
        if task_id not in tasks_cache:
            return jsonify({"error": "Task not found"}), 404

        async with httpx.AsyncClient() as client:
            external_response = await client.delete(f"{FAKER_API_URL}/Tasks/{task_id}")
            external_response.raise_for_status()

        del tasks_cache[task_id]
        return jsonify({"message": "Task deleted successfully"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to delete task"}), 500

@app.route('/authentication', methods=['POST'])
@validate_request(AuthenticationData)  # Works around the quart-schema ordering issue for POST requests
async def authentication(data: AuthenticationData):
    try:
        async with httpx.AsyncClient() as client:
            external_response = await client.post(f"{FAKER_API_URL}/Authentication", json=data.__dict__)
            external_response.raise_for_status()
            auth_data = external_response.json()

        # TODO: Implement token verification and secure session management
        return jsonify(auth_data)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Authentication failed"}), 500

@app.route('/activities', methods=['GET'])
async def get_activities():
    # Return local cache of activities (TODO: Expand as needed)
    return jsonify(activities_cache)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)