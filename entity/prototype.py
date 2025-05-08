from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

FAKEREST_BASE = "https://fakerestapi.azurewebsites.net/api/v1"
auth_tokens: Dict[str, Dict[str, Any]] = {}
entity_jobs: Dict[str, Dict[str, Any]] = {}

def generate_job_id() -> str:
    return datetime.utcnow().isoformat() + "-" + str(len(entity_jobs) + 1)

async def fetch_external_api(method: str, url: str, json: Optional[Dict] = None) -> Dict:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.request(method, url, json=json, timeout=10)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as e:
        logger.exception(f"External API request failed: {e}")
        raise

@dataclass
class AuthLogin:
    username: str
    password: str

@dataclass
class AuthLogout:
    access_token: str

@dataclass
class SearchPage:
    search: Optional[str] = None
    page: Optional[int] = 1
    page_size: Optional[int] = 20

@dataclass
class BookCreate:
    title: str
    description: str
    author_id: int

@dataclass
class BookUpdate:
    id: int
    title: Optional[str] = None
    description: Optional[str] = None
    author_id: Optional[int] = None

@dataclass
class BookDelete:
    id: int

@dataclass
class AuthorCreate:
    name: str

@dataclass
class AuthorUpdate:
    id: int
    name: Optional[str] = None

@dataclass
class AuthorDelete:
    id: int

@dataclass
class UserCreate:
    name: str
    email: str

@dataclass
class UserUpdate:
    id: int
    name: Optional[str] = None
    email: Optional[str] = None

@dataclass
class UserDelete:
    id: int

@dataclass
class TaskSearchPage:
    search: Optional[str] = None
    page: Optional[int] = 1
    page_size: Optional[int] = 20

@dataclass
class ActivitiesList:
    user_id: Optional[int] = None
    date_range: Optional[Dict[str, str]] = None

@dataclass
class JobId:
    job_id: str

@app.route("/auth/login", methods=["POST"])
@validate_request(AuthLogin)  # POST validation last due to quart-schema issue workaround
async def login(data: AuthLogin):
    try:
        resp = await fetch_external_api(
            "POST", f"{FAKEREST_BASE}/Authentication", json={"userName": data.username, "password": data.password}
        )
        token = resp.get("token")
        if not token:
            return jsonify({"message": "Authentication failed"}), 401
        auth_tokens[token] = {"username": data.username, "expires_in": 3600, "created_at": datetime.utcnow()}
        return jsonify({"access_token": token, "expires_in": 3600})
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Authentication error"}), 500

@app.route("/auth/logout", methods=["POST"])
@validate_request(AuthLogout)  # POST validation last due to quart-schema issue workaround
async def logout(data: AuthLogout):
    token = data.access_token
    if token in auth_tokens:
        auth_tokens.pop(token)
        return jsonify({"message": "Logged out successfully"})
    else:
        return jsonify({"message": "Invalid token"}), 400

@app.route("/books/list", methods=["POST"])
@validate_request(SearchPage)  # POST validation last
async def books_list(data: SearchPage):
    search = (data.search or "").lower()
    page = data.page or 1
    page_size = data.page_size or 20
    try:
        books = await fetch_external_api("GET", f"{FAKEREST_BASE}/Books")
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
@validate_request(BookCreate)  # POST validation last
async def books_create(data: BookCreate):
    job_id = generate_job_id()
    entity_jobs[job_id] = {"status": "queued", "requestedAt": datetime.utcnow().isoformat()}
    await asyncio.create_task(
        process_entity(
            entity_jobs,
            job_id,
            "POST",
            f"{FAKEREST_BASE}/Books",
            {
                "title": data.title,
                "description": data.description,
                "pageCount": 0,  # TODO placeholder
                "excerpt": "",
                "publishDate": datetime.utcnow().isoformat(),
                "author": data.author_id,
            },
        )
    )
    return jsonify({"job_id": job_id, "message": "Book creation started"})

@app.route("/books/update", methods=["POST"])
@validate_request(BookUpdate)  # POST validation last
async def books_update(data: BookUpdate):
    book_id = data.id
    if not book_id:
        return jsonify({"message": "Book id required"}), 400
    job_id = generate_job_id()
    entity_jobs[job_id] = {"status": "queued", "requestedAt": datetime.utcnow().isoformat()}
    try:
        original = await fetch_external_api("GET", f"{FAKEREST_BASE}/Books/{book_id}")
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Book not found"}), 404
    payload = {
        "id": book_id,
        "title": data.title or original.get("title"),
        "description": data.description or original.get("description"),
        "pageCount": original.get("pageCount", 0),
        "excerpt": original.get("excerpt", ""),
        "publishDate": original.get("publishDate", datetime.utcnow().isoformat()),
        "author": data.author_id or original.get("author", 0),
    }
    await asyncio.create_task(
        process_entity(entity_jobs, job_id, "PUT", f"{FAKEREST_BASE}/Books/{book_id}", payload)
    )
    return jsonify({"job_id": job_id, "message": "Book update started"})

@app.route("/books/delete", methods=["POST"])
@validate_request(BookDelete)  # POST validation last
async def books_delete(data: BookDelete):
    book_id = data.id
    if not book_id:
        return jsonify({"message": "Book id required"}), 400
    job_id = generate_job_id()
    entity_jobs[job_id] = {"status": "queued", "requestedAt": datetime.utcnow().isoformat()}
    await asyncio.create_task(
        process_entity(entity_jobs, job_id, "DELETE", f"{FAKEREST_BASE}/Books/{book_id}", {})
    )
    return jsonify({"job_id": job_id, "message": "Book deletion started"})

@app.route("/authors/list", methods=["POST"])
@validate_request(SearchPage)  # POST validation last
async def authors_list(data: SearchPage):
    search = (data.search or "").lower()
    page = data.page or 1
    page_size = data.page_size or 20
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
@validate_request(AuthorCreate)  # POST validation last
async def authors_create(data: AuthorCreate):
    job_id = generate_job_id()
    entity_jobs[job_id] = {"status": "queued", "requestedAt": datetime.utcnow().isoformat()}
    name = data.name
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
                "id": 0,  # TODO placeholder
                "idBook": 0,  # TODO placeholder
                "firstName": first_name,
                "lastName": last_name,
            },
        )
    )
    return jsonify({"job_id": job_id, "message": "Author creation started"})

@app.route("/authors/update", methods=["POST"])
@validate_request(AuthorUpdate)  # POST validation last
async def authors_update(data: AuthorUpdate):
    author_id = data.id
    if not author_id:
        return jsonify({"message": "Author id required"}), 400
    job_id = generate_job_id()
    entity_jobs[job_id] = {"status": "queued", "requestedAt": datetime.utcnow().isoformat()}
    try:
        original = await fetch_external_api("GET", f"{FAKEREST_BASE}/Authors/{author_id}")
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Author not found"}), 404
    if data.name:
        parts = data.name.split(" ", 1)
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
@validate_request(AuthorDelete)  # POST validation last
async def authors_delete(data: AuthorDelete):
    author_id = data.id
    if not author_id:
        return jsonify({"message": "Author id required"}), 400
    job_id = generate_job_id()
    entity_jobs[job_id] = {"status": "queued", "requestedAt": datetime.utcnow().isoformat()}
    await asyncio.create_task(
        process_entity(entity_jobs, job_id, "DELETE", f"{FAKEREST_BASE}/Authors/{author_id}", {})
    )
    return jsonify({"job_id": job_id, "message": "Author deletion started"})

@app.route("/users/list", methods=["POST"])
@validate_request(SearchPage)  # POST validation last
async def users_list(data: SearchPage):
    search = (data.search or "").lower()
    page = data.page or 1
    page_size = data.page_size or 20
    try:
        users = await fetch_external_api("GET", f"{FAKEREST_BASE}/Users")
        if search:
            users = [u for u in users if search in u.get("userName", "").lower() or search in u.get("email", "").lower()]
        total = len(users)
        start = (page - 1) * page_size
        end = start + page_size
        paged = users[start:end]
        mapped = [{"id": u["id"], "name": u.get("userName", ""), "email": u.get("email", "")} for u in paged]
        return jsonify({"users": mapped, "total": total})
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Failed to retrieve users"}), 500

@app.route("/users/create", methods=["POST"])
@validate_request(UserCreate)  # POST validation last
async def users_create(data: UserCreate):
    job_id = generate_job_id()
    entity_jobs[job_id] = {"status": "queued", "requestedAt": datetime.utcnow().isoformat()}
    payload = {
        "id": 0,  # TODO placeholder
        "userName": data.name,
        "password": "changeme",  # TODO placeholder
        "fullName": data.name,
        "email": data.email,
        "avatar": "",
    }
    await asyncio.create_task(
        process_entity(entity_jobs, job_id, "POST", f"{FAKEREST_BASE}/Users", payload)
    )
    return jsonify({"job_id": job_id, "message": "User creation started"})

@app.route("/users/update", methods=["POST"])
@validate_request(UserUpdate)  # POST validation last
async def users_update(data: UserUpdate):
    user_id = data.id
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
        "userName": data.name or original.get("userName"),
        "password": original.get("password", "changeme"),
        "fullName": data.name or original.get("fullName"),
        "email": data.email or original.get("email"),
        "avatar": original.get("avatar", ""),
    }
    await asyncio.create_task(
        process_entity(entity_jobs, job_id, "PUT", f"{FAKEREST_BASE}/Users/{user_id}", payload)
    )
    return jsonify({"job_id": job_id, "message": "User update started"})

@app.route("/users/delete", methods=["POST"])
@validate_request(UserDelete)  # POST validation last
async def users_delete(data: UserDelete):
    user_id = data.id
    if not user_id:
        return jsonify({"message": "User id required"}), 400
    job_id = generate_job_id()
    entity_jobs[job_id] = {"status": "queued", "requestedAt": datetime.utcnow().isoformat()}
    await asyncio.create_task(
        process_entity(entity_jobs, job_id, "DELETE", f"{FAKEREST_BASE}/Users/{user_id}", {})
    )
    return jsonify({"job_id": job_id, "message": "User deletion started"})

@app.route("/tasks/list", methods=["POST"])
@validate_request(TaskSearchPage)  # POST validation last
async def tasks_list(data: TaskSearchPage):
    search = (data.search or "").lower()
    page = data.page or 1
    page_size = data.page_size or 20
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

# Removed @validate_request decorator because dict is not supported by quart-schema
@app.route("/tasks/create", methods=["POST"])
async def tasks_create():
    return jsonify({"message": "Task creation not implemented in FakeRest API"}), 501

# Removed @validate_request decorator because dict is not supported by quart-schema
@app.route("/tasks/update", methods=["POST"])
async def tasks_update():
    return jsonify({"message": "Task update not implemented in FakeRest API"}), 501

# Removed @validate_request decorator because dict is not supported by quart-schema
@app.route("/tasks/delete", methods=["POST"])
async def tasks_delete():
    return jsonify({"message": "Task deletion not implemented in FakeRest API"}), 501

@dataclass
class ActivitiesListRequest:
    user_id: Optional[int] = None
    date_range: Optional[Dict[str, str]] = None

@app.route("/activities/list", methods=["POST"])
@validate_request(ActivitiesListRequest)  # POST validation last
async def activities_list(data: ActivitiesListRequest):
    user_id = data.user_id
    # date_range ignored in prototype (TODO)
    try:
        activities = await fetch_external_api("GET", f"{FAKEREST_BASE}/Activities")
        if user_id is not None:
            activities = [a for a in activities if a.get("userId") == user_id]
        return jsonify({"activities": activities})
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Failed to retrieve activities"}), 500

@app.route("/jobs/<job_id>", methods=["GET"])
async def job_status(job_id):
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"message": "Job not found"}), 404
    return jsonify(job)

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

if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
