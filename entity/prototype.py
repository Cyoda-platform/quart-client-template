import asyncio
import datetime
import logging
import uuid

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

BASE_URL = "https://fakerestapi.azurewebsites.net/api"

# In-memory persistence (local caches)
books = {}
authors = {}
users = {}
tasks_store = {}
activities = []


async def process_entity(entity_job, data):
    try:
        # Simulate asynchronous processing (e.g. complex calculations or data gathering)
        await asyncio.sleep(1)
        # Update job status upon completion
        entity_job["status"] = "completed"
    except Exception as e:
        logger.exception(e)


# -------------------------
# Book Management Endpoints
# -------------------------

@app.route('/api/books', methods=['GET'])
async def get_books():
    return jsonify({"books": list(books.values())})


@app.route('/api/books', methods=['POST'])
async def add_book():
    data = await request.get_json()
    try:
        async with httpx.AsyncClient() as client:
            # Call real API endpoint to add a book
            response = await client.post(f"{BASE_URL}/Books", json=data)
            response.raise_for_status()
            result = response.json()
            # TODO: Determine proper mapping based on external API response.
            book_id = result.get("id") or str(uuid.uuid4())
            data["id"] = book_id
            books[book_id] = data
            return jsonify({"message": "Book added successfully.", "bookId": book_id})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500


@app.route('/api/books/update', methods=['POST'])
async def update_book():
    data = await request.get_json()
    try:
        book_id = data.get("id")
        if book_id not in books:
            return jsonify({"error": "Book not found."}), 404

        async with httpx.AsyncClient() as client:
            # Using PUT for update operation to external API
            response = await client.put(f"{BASE_URL}/Books/{book_id}", json=data)
            response.raise_for_status()
            books[book_id] = data
            return jsonify({"message": "Book updated successfully."})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500


@app.route('/api/books/delete', methods=['POST'])
async def delete_book():
    data = await request.get_json()
    book_id = data.get("id")
    try:
        if book_id not in books:
            return jsonify({"error": "Book not found."}), 404
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{BASE_URL}/Books/{book_id}")
            response.raise_for_status()
            del books[book_id]
            return jsonify({"message": "Book deleted successfully."})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500


# ---------------------------
# Author Management Endpoints
# ---------------------------

@app.route('/api/authors', methods=['GET'])
async def get_authors():
    return jsonify({"authors": list(authors.values())})


@app.route('/api/authors', methods=['POST'])
async def add_author():
    data = await request.get_json()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{BASE_URL}/Authors", json=data)
            response.raise_for_status()
            result = response.json()
            # TODO: Confirm external API response format.
            author_id = result.get("id") or str(uuid.uuid4())
            data["id"] = author_id
            authors[author_id] = data
            return jsonify({"message": "Author added successfully.", "authorId": author_id})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500


@app.route('/api/authors/update', methods=['POST'])
async def update_author():
    data = await request.get_json()
    try:
        author_id = data.get("id")
        if author_id not in authors:
            return jsonify({"error": "Author not found."}), 404
        async with httpx.AsyncClient() as client:
            response = await client.put(f"{BASE_URL}/Authors/{author_id}", json=data)
            response.raise_for_status()
            authors[author_id] = data
            return jsonify({"message": "Author updated successfully."})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500


@app.route('/api/authors/delete', methods=['POST'])
async def delete_author():
    data = await request.get_json()
    author_id = data.get("id")
    try:
        if author_id not in authors:
            return jsonify({"error": "Author not found."}), 404
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{BASE_URL}/Authors/{author_id}")
            response.raise_for_status()
            del authors[author_id]
            return jsonify({"message": "Author deleted successfully."})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500


# ------------------------
# User Management Endpoints
# ------------------------

@app.route('/api/users', methods=['GET'])
async def get_users():
    return jsonify({"users": list(users.values())})


@app.route('/api/users', methods=['POST'])
async def create_user():
    data = await request.get_json()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{BASE_URL}/Users", json=data)
            response.raise_for_status()
            result = response.json()
            user_id = result.get("id") or str(uuid.uuid4())
            data["id"] = user_id
            users[user_id] = data
            return jsonify({"message": "User created successfully.", "userId": user_id})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500


@app.route('/api/users/update', methods=['POST'])
async def update_user():
    data = await request.get_json()
    try:
        user_id = data.get("id")
        if user_id not in users:
            return jsonify({"error": "User not found."}), 404
        async with httpx.AsyncClient() as client:
            response = await client.put(f"{BASE_URL}/Users/{user_id}", json=data)
            response.raise_for_status()
            users[user_id] = data
            return jsonify({"message": "User updated successfully."})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500


@app.route('/api/users/delete', methods=['POST'])
async def delete_user():
    data = await request.get_json()
    user_id = data.get("id")
    try:
        if user_id not in users:
            return jsonify({"error": "User not found."}), 404
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{BASE_URL}/Users/{user_id}", json=data)
            response.raise_for_status()
            del users[user_id]
            return jsonify({"message": "User deleted successfully."})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500


# -------------------------
# Task Management Endpoints
# -------------------------

@app.route('/api/tasks', methods=['GET'])
async def get_tasks():
    return jsonify({"tasks": list(tasks_store.values())})


@app.route('/api/tasks', methods=['POST'])
async def add_task():
    data = await request.get_json()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{BASE_URL}/Tasks", json=data)
            response.raise_for_status()
            result = response.json()
            task_id = result.get("id") or str(uuid.uuid4())
            data["id"] = task_id
            tasks_store[task_id] = data
            return jsonify({"message": "Task added successfully.", "taskId": task_id})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500


@app.route('/api/tasks/update', methods=['POST'])
async def update_task():
    data = await request.get_json()
    try:
        task_id = data.get("id")
        if task_id not in tasks_store:
            return jsonify({"error": "Task not found."}), 404
        async with httpx.AsyncClient() as client:
            response = await client.put(f"{BASE_URL}/Tasks/{task_id}", json=data)
            response.raise_for_status()
            tasks_store[task_id] = data
            return jsonify({"message": "Task updated successfully."})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500


@app.route('/api/tasks/delete', methods=['POST'])
async def delete_task():
    data = await request.get_json()
    task_id = data.get("id")
    try:
        if task_id not in tasks_store:
            return jsonify({"error": "Task not found."}), 404
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{BASE_URL}/Tasks/{task_id}", json=data)
            response.raise_for_status()
            del tasks_store[task_id]
            return jsonify({"message": "Task deleted successfully."})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500


# ------------------------
# Authentication Endpoints
# ------------------------

@app.route('/api/authentication/login', methods=['POST'])
async def login():
    data = await request.get_json()
    try:
        async with httpx.AsyncClient() as client:
            # TODO: Confirm external API's actual authentication payload and response format.
            response = await client.post(f"{BASE_URL}/Authentication", json=data)
            response.raise_for_status()
            result = response.json()
            token = result.get("token") or str(uuid.uuid4())  # Fallback to a generated token
            return jsonify({"message": "Login successful.", "token": token})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500


@app.route('/api/authentication/logout', methods=['POST'])
async def logout():
    data = await request.get_json()
    try:
        async with httpx.AsyncClient() as client:
            # TODO: Confirm external logout endpoint and any required payload.
            response = await client.post(f"{BASE_URL}/Authentication/Logout", json=data)
            response.raise_for_status()
            return jsonify({"message": "Logout successful."})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500


# ------------------------
# User Activities Endpoint
# ------------------------

@app.route('/api/activities', methods=['GET'])
async def get_activities():
    return jsonify({"activities": activities})


def log_activity(activity):
    entry = {
        "id": str(uuid.uuid4()),
        "activity": activity,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    activities.append(entry)


# ------------------------
# Example Fire-and-Forget Processing Endpoint
# ------------------------

@app.route('/api/process', methods=['POST'])
async def process_entity_endpoint():
    data = await request.get_json()
    job_id = str(uuid.uuid4())
    requested_at = datetime.datetime.utcnow().isoformat()
    entity_job = {"status": "processing", "requestedAt": requested_at}
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(entity_job, data))
    # TODO: In a full implementation, persist job status and link to user notifications.
    return jsonify({"message": "Processing started.", "jobId": job_id})


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)