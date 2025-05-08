```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Base URL for the FakeRest API
FAKEREST_BASE = "https://fakerestapi.azurewebsites.net/api/v1"

# In-memory caches / local state for prototype (no real persistence)
auth_tokens: Dict[str, Dict[str, Any]] = {}  # token -> user info (mock)
entity_jobs: Dict[str, Dict[str, Any]] = {}  # job_id -> status info

# Simple utility to generate job ids for async tasks
def generate_job_id() -> str:
    return datetime.utcnow().isoformat() + "-" + str(len(entity_jobs) + 1)


# --- Helper HTTP client context manager ---
async def fetch_external_api(method: str, url: str, json: Optional[Dict] = None) -> Dict:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.request(method, url, json=json, timeout=10)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as e:
        logger.exception(f"External API request failed: {e}")
        raise


# --- Authentication ---

@app.route("/auth/login", methods=["POST"])
async def login():
    data = await request.get_json()
    username = data.get("username")
    password = data.get("password")

    # Call external Authentication endpoint
    try:
        # FakeRestAPI /Authentication expects username/password in POST body
        resp = await fetch_external_api(
            "POST", f"{FAKEREST_BASE}/Authentication", json={"userName": username, "password": password}
        )
        token = resp.get("token")
        if not token:
            return jsonify({"message": "Authentication failed"}), 401

        # Mock token storage with expiry info; no user roles implemented yet
        auth_tokens[token] = {"username": username, "expires_in": 3600, "created_at": datetime.utcnow()}

        return jsonify({"access_token": token, "expires_in": 3600})
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Authentication error"}), 500


@app.route("/auth/logout", methods=["POST"])
async def logout():
    data = await request.get_json()
    token = data.get("access_token")
    if token in auth_tokens:
        auth_tokens.pop(token)
        return jsonify({"message": "Logged out successfully"})
    else:
        return jsonify({"message": "Invalid token"}), 400


# --- Utility: Require authentication token from header ---

async def get_auth_token() -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        if token in auth_tokens:
            return token
    return None


# --- Entity processing pattern for POST endpoints that invoke external APIs ---

async def process_entity(entity_job: Dict[str, Dict[str, Any]], job_id: str, method: str, url: str, payload: Dict[str, Any]):
    try:
        entity_job[job_id]["status"] = "processing"
        result = await fetch_external_api(method, url, json=payload)
        entity_job[job_id]["status"] = "completed"
        entity_job[job_id]["result"] = result
        entity_job[job_id]["completedAt"] = datetime.utcnow().isoformat()
    except Exception as e:
        entity_job[job_id]["status"] = "failed"
        entity_job[job_id]["error"] = str(e)
        logger.exception(e)


# --- Books ---

@app.route("/books/list", methods=["POST"])
async def books_list():
    # Retrieve books list from external API and apply search + pagination in-app
    data = await request.get_json()
    search = data.get("search", "").lower()
    page = int(data.get("page", 1))
    page_size = int(data.get("page_size", 20))

    try:
        books = await fetch_external_api("GET", f"{FAKEREST_BASE}/Books")
        # Filter by search (title contains)
        if search:
            books = [b for b in books if search in b.get("title", "").lower()]
        total = len(books)
        start = (page - 1) * page_size
        end = start + page_size
        paged = books[start:end]
        return jsonify({"books": paged, "total": total})
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Failed to retrieve books"}), 500


@app.route("/books/create", methods=["POST"])
async def books_create():
    data = await request.get_json()
    job_id = generate_job_id()
    entity_jobs[job_id] = {"status": "queued", "requestedAt": datetime.utcnow().isoformat()}

    # Fire and forget
    await asyncio.create_task(
        process_entity(
            entity_jobs,
            job_id,
            "POST",
            f"{FAKEREST_BASE}/Books",
            {
                "title": data.get("title"),
                "description": data.get("description"),
                "pageCount": 0,  # TODO: FakeRest requires pageCount, using 0 as placeholder
                "excerpt": "",
                "publishDate": datetime.utcnow().isoformat(),
                "author": data.get("author_id", 0),  # TODO: Mapping author_id to author field
            },
        )
    )
    return jsonify({"job_id": job_id, "message": "Book creation started"})


@app.route("/books/update", methods=["POST"])
async def books_update():
    data = await request.get_json()
    book_id = data.get("id")
    if not book_id:
        return jsonify({"message": "Book id required"}), 400
    job_id = generate_job_id()
    entity_jobs[job_id] = {"status": "queued", "requestedAt": datetime.utcnow().isoformat()}

    # Fetch original book to merge fields (FakeRest requires full object on PUT)
    try:
        original = await fetch_external_api("GET", f"{FAKEREST_BASE}/Books/{book_id}")
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Book not found"}), 404

    payload = {
        "id": book_id,
        "title": data.get("title", original.get("title")),
        "description": data.get("description", original.get("description")),
        "pageCount": original.get("pageCount", 0),
        "excerpt": original.get("excerpt", ""),
        "publishDate": original.get("publishDate", datetime.utcnow().isoformat()),
        "author": data.get("author_id", original.get("author", 0)),
    }

    await asyncio.create_task(
        process_entity(entity_jobs, job_id, "PUT", f"{FAKEREST_BASE}/Books/{book_id}", payload)
    )
    return jsonify({"job_id": job_id, "message": "Book update started"})


@app.route("/books/delete", methods=["POST"])
async def books_delete():
    data = await request.get_json()
    book_id = data.get("id")
    if not book_id:
        return jsonify({"message": "Book id required"}), 400
    job_id = generate_job_id()
    entity_jobs[job_id] = {"status": "queued", "requestedAt": datetime.utcnow().isoformat()}

    await asyncio.create_task(
        process_entity(entity_jobs, job_id, "DELETE", f"{FAKEREST_BASE}/Books/{book_id}", {})
    )
    return jsonify({"job_id": job_id, "message": "Book deletion started"})


# --- Authors ---

@app.route("/authors/list", methods=["POST"])
async def authors_list():
    data = await request.get_json()
    search = data.get("search", "").lower()
    page = int(data.get("page", 1))
    page_size = int(data.get("page_size", 20))

    try:
        authors = await fetch_external_api("GET", f"{FAKEREST_BASE}/Authors")
        if search:
            authors = [a for a in authors if search in a.get("name", "").lower()]
        total = len(authors)
        start = (page - 1) * page_size
        end = start + page_size
        paged = authors[start:end]
        return jsonify({"authors": paged, "total": total})
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Failed to retrieve authors"}), 500


@app.route("/authors/create", methods=["POST"])
async def authors_create():
    data = await request.get_json()
    job_id = generate_job_id()
    entity_jobs[job_id] = {"status": "queued", "requestedAt": datetime.utcnow().isoformat()}

    # FakeRest API for authors requires: id, idBook, firstName, lastName
    # TODO: Mapping input fields appropriately; using name split as placeholder
    name = data.get("name", "")
    parts = name.split(" ", 1)
    first_name = parts[0] if parts else ""
    last_name = parts[1] if len(parts) > 1 else ""

    await asyncio.create_task(
        process_entity(
            entity_jobs,
            job_id,
            "POST",
            f"{FAKEREST_BASE}/Authors",
            {
                "id": 0,  # TODO: FakeRest requires id for authors, 0 as placeholder - might fail
                "idBook": 0,  # TODO: Link author to book; 0 placeholder
                "firstName": first_name,
                "lastName": last_name,
            },
        )
    )
    return jsonify({"job_id": job_id, "message": "Author creation started"})


@app.route("/authors/update", methods=["POST"])
async def authors_update():
    data = await request.get_json()
    author_id = data.get("id")
    if not author_id:
        return jsonify({"message": "Author id required"}), 400
    job_id = generate_job_id()
    entity_jobs[job_id] = {"status": "queued", "requestedAt": datetime.utcnow().isoformat()}

    # Fetch original author for merging fields
    try:
        original = await fetch_external_api("GET", f"{FAKEREST_BASE}/Authors/{author_id}")
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Author not found"}), 404

    name = data.get("name", "")
    if name:
        parts = name.split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""
    else:
        first_name = original.get("firstName")
        last_name = original.get("lastName")

    payload = {
        "id": author_id,
        "idBook": original.get("idBook", 0),
        "firstName": first_name,
        "lastName": last_name,
    }

    await asyncio.create_task(
        process_entity(entity_jobs, job_id, "PUT", f"{FAKEREST_BASE}/Authors/{author_id}", payload)
    )
    return jsonify({"job_id": job_id, "message": "Author update started"})


@app.route("/authors/delete", methods=["POST"])
async def authors_delete():
    data = await request.get_json()
    author_id = data.get("id")
    if not author_id:
        return jsonify({"message": "Author id required"}), 400
    job_id = generate_job_id()
    entity_jobs[job_id] = {"status": "queued", "requestedAt": datetime.utcnow().isoformat()}

    await asyncio.create_task(
        process_entity(entity_jobs, job_id, "DELETE", f"{FAKEREST_BASE}/Authors/{author_id}", {})
    )
    return jsonify({"job_id": job_id, "message": "Author deletion started"})


# --- Users ---

@app.route("/users/list", methods=["POST"])
async def users_list():
    data = await request.get_json()
    search = data.get("search", "").lower()
    page = int(data.get("page", 1))
    page_size = int(data.get("page_size", 20))

    try:
        users = await fetch_external_api("GET", f"{FAKEREST_BASE}/Users")
        if search:
            users = [u for u in users if search in u.get("userName", "").lower() or search in u.get("email", "").lower()]
        total = len(users)
        start = (page - 1) * page_size
        end = start + page_size
        paged = users[start:end]
        # Map external fields to simplified fields
        mapped = [
            {"id": u["id"], "name": u.get("userName", ""), "email": u.get("email", "")} for u in paged
        ]
        return jsonify({"users": mapped, "total": total})
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Failed to retrieve users"}), 500


@app.route("/users/create", methods=["POST"])
async def users_create():
    data = await request.get_json()
    job_id = generate_job_id()
    entity_jobs[job_id] = {"status": "queued", "requestedAt": datetime.utcnow().isoformat()}

    # FakeRest requires: id, userName, password, fullName, email, avatar
    # TODO: Password and avatar fields missing, placeholder used
    payload = {
        "id": 0,  # TODO: id required, 0 as placeholder
        "userName": data.get("name", ""),
        "password": "changeme",  # TODO: no password provided, default placeholder
        "fullName": data.get("name", ""),
        "email": data.get("email", ""),
        "avatar": "",
    }

    await asyncio.create_task(
        process_entity(entity_jobs, job_id, "POST", f"{FAKEREST_BASE}/Users", payload)
    )
    return jsonify({"job_id": job_id, "message": "User creation started"})


@app.route("/users/update", methods=["POST"])
async def users_update():
    data = await request.get_json()
    user_id = data.get("id")
    if not user_id:
        return jsonify({"message": "User id required"}), 400
    job_id = generate_job_id()
    entity_jobs[job_id] = {"status": "queued", "requestedAt": datetime.utcnow().isoformat()}

    try:
        original = await fetch_external_api("GET", f"{FAKEREST_BASE}/Users/{user_id}")
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "User not found"}), 404

    payload = {
        "id": user_id,
        "userName": data.get("name", original.get("userName")),
        "password": original.get("password", "changeme"),
        "fullName": data.get("name", original.get("fullName")),
        "email": data.get("email", original.get("email")),
        "avatar": original.get("avatar", ""),
    }

    await asyncio.create_task(
        process_entity(entity_jobs, job_id, "PUT", f"{FAKEREST_BASE}/Users/{user_id}", payload)
    )
    return jsonify({"job_id": job_id, "message": "User update started"})


@app.route("/users/delete", methods=["POST"])
async def users_delete():
    data = await request.get_json()
    user_id = data.get("id")
    if not user_id:
        return jsonify({"message": "User id required"}), 400
    job_id = generate_job_id()
    entity_jobs[job_id] = {"status": "queued", "requestedAt": datetime.utcnow().isoformat()}

    await asyncio.create_task(
        process_entity(entity_jobs, job_id, "DELETE", f"{FAKEREST_BASE}/Users/{user_id}", {})
    )
    return jsonify({"job_id": job_id, "message": "User deletion started"})


# --- Tasks ---

@app.route("/tasks/list", methods=["POST"])
async def tasks_list():
    data = await request.get_json()
    search = data.get("search", "").lower()
    page = int(data.get("page", 1))
    page_size = int(data.get("page_size", 20))

    try:
        tasks = await fetch_external_api("GET", f"{FAKEREST_BASE}/Activities")
        if search:
            tasks = [t for t in tasks if search in t.get("title", "").lower()]
        total = len(tasks)
        start = (page - 1) * page_size
        end = start + page_size
        paged = tasks[start:end]
        return jsonify({"tasks": paged, "total": total})
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Failed to retrieve tasks"}), 500


@app.route("/tasks/create", methods=["POST"])
async def tasks_create():
    # FakeRest API does not have a direct /Tasks endpoint, using /Activities as placeholder
    # TODO: Implement real tasks API integration when available
    data = await request.get_json()
    return jsonify({"message": "Task creation not implemented in FakeRest API"}), 501


@app.route("/tasks/update", methods=["POST"])
async def tasks_update():
    # TODO: Implement real tasks API integration when available
    return jsonify({"message": "Task update not implemented in FakeRest API"}), 501


@app.route("/tasks/delete", methods=["POST"])
async def tasks_delete():
    # TODO: Implement real tasks API integration when available
    return jsonify({"message": "Task deletion not implemented in FakeRest API"}), 501


# --- User Activities ---

@app.route("/activities/list", methods=["POST"])
async def activities_list():
    data = await request.get_json()
    user_id = data.get("user_id")
    date_range = data.get("date_range", {})
    # FakeRest /Activities endpoint returns all activities; no filtering supported
    try:
        activities = await fetch_external_api("GET", f"{FAKEREST_BASE}/Activities")
        # Filter by user_id if provided
        if user_id is not None:
            activities = [a for a in activities if a.get("userId") == user_id]
        # Date filtering is skipped (TODO)
        return jsonify({"activities": activities})
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Failed to retrieve activities"}), 500


# --- Job status endpoint (optional) ---

@app.route("/jobs/<job_id>", methods=["GET"])
async def job_status(job_id):
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"message": "Job not found"}), 404
    return jsonify(job)


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
