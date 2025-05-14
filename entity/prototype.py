from dataclasses import dataclass
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request, abort
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Request models
@dataclass
class CreateBugRequest:
    title: str
    description: str
    reported_by: str
    severity: str
    steps_to_reproduce: Optional[str] = None

@dataclass
class UpdateBugRequest:
    status: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    steps_to_reproduce: Optional[str] = None

@dataclass
class AddCommentRequest:
    author: str
    message: str

@dataclass
class ListBugsQuery:
    status: Optional[str] = None
    severity: Optional[str] = None
    search: Optional[str] = None
    page: Optional[int] = None
    page_size: Optional[int] = None
    sort_by: Optional[str] = None
    sort_order: Optional[str] = None

# In-memory storage
bugs: Dict[str, dict] = {}
comments: Dict[str, List[dict]] = {}
bugs_lock = asyncio.Lock()
comments_lock = asyncio.Lock()

SEVERITY_LEVELS = {"low", "medium", "high"}
STATUS_VALUES = {"open", "in_progress", "closed"}

def iso8601_now() -> str:
    return datetime.utcnow().isoformat() + "Z"

def validate_bug_input(data: dict, update: bool = False):
    if not update:
        if "title" not in data or not isinstance(data["title"], str) or not data["title"].strip():
            abort(400, "Field 'title' is required and must be non-empty string")
        if "description" not in data or not isinstance(data["description"], str):
            abort(400, "Field 'description' is required and must be string")
        if "reported_by" not in data or not isinstance(data["reported_by"], str):
            abort(400, "Field 'reported_by' is required and must be string")
        if "severity" not in data or data["severity"] not in SEVERITY_LEVELS:
            abort(400, f"Field 'severity' is required and must be one of {SEVERITY_LEVELS}")
        if "steps_to_reproduce" in data and not isinstance(data["steps_to_reproduce"], str):
            abort(400, "Field 'steps_to_reproduce' must be string if provided")
    else:
        if "status" in data and data["status"] not in STATUS_VALUES:
            abort(400, f"Field 'status' must be one of {STATUS_VALUES}")
        for field in ["description", "steps_to_reproduce"]:
            if field in data and not isinstance(data[field], str):
                abort(400, f"Field '{field}' must be string if provided")
        if "severity" in data and data["severity"] not in SEVERITY_LEVELS:
            abort(400, f"Field 'severity' must be one of {SEVERITY_LEVELS}")

def validate_comment_input(data: dict):
    if "author" not in data or not isinstance(data["author"], str) or not data["author"].strip():
        abort(400, "Field 'author' is required and must be non-empty string")
    if "message" not in data or not isinstance(data["message"], str) or not data["message"].strip():
        abort(400, "Field 'message' is required and must be non-empty string")

@app.route("/api/bugs", methods=["POST"])
@validate_request(CreateBugRequest)  # validation last for POST (workaround issue)
async def create_bug(data: CreateBugRequest):
    payload = data.__dict__
    validate_bug_input(payload)
    bug_id = str(uuid.uuid4())
    now = iso8601_now()
    bug = {
        "bug_id": bug_id,
        "title": data.title.strip(),
        "description": data.description.strip(),
        "reported_by": data.reported_by.strip(),
        "severity": data.severity,
        "status": "open",
        "steps_to_reproduce": (data.steps_to_reproduce or "").strip(),
        "created_at": now,
        "updated_at": now,
    }
    async with bugs_lock:
        bugs[bug_id] = bug
    async with comments_lock:
        comments[bug_id] = []
    logger.info(f"Created bug {bug_id}")
    return jsonify({"bug_id": bug_id, "status": "open", "created_at": now}), 201

@validate_querystring(ListBugsQuery)  # validation first for GET (workaround issue)
@app.route("/api/bugs", methods=["GET"])
async def list_bugs():
    status_filter = request.args.get("status")
    severity_filter = request.args.get("severity")
    search = request.args.get("search", "").strip().lower()
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1
    try:
        page_size = max(1, min(100, int(request.args.get("page_size", 20))))
    except ValueError:
        page_size = 20
    sort_by = request.args.get("sort_by", "created_at")
    sort_order = request.args.get("sort_order", "desc")
    sort_order = sort_order if sort_order in {"asc", "desc"} else "desc"

    async with bugs_lock:
        all_bugs = list(bugs.values())

    def bug_matches(bug):
        if status_filter and bug["status"] != status_filter:
            return False
        if severity_filter and bug["severity"] != severity_filter:
            return False
        if search and search not in bug["title"].lower() and search not in bug["description"].lower():
            return False
        return True

    filtered = list(filter(bug_matches, all_bugs))
    reverse = sort_order == "desc"
    if sort_by in {"created_at", "severity", "status"}:
        if sort_by == "severity":
            severity_order = {"low": 0, "medium": 1, "high": 2}
            def key_func(b): return severity_order.get(b["severity"], -1)
        else:
            def key_func(b): return b.get(sort_by, "")
        filtered.sort(key=key_func, reverse=reverse)

    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    paged = filtered[start:end]
    bugs_list = [
        {"bug_id": b["bug_id"], "title": b["title"], "status": b["status"],
         "severity": b["severity"], "created_at": b["created_at"]}
        for b in paged
    ]
    return jsonify({"total": total, "page": page, "page_size": page_size, "bugs": bugs_list})

@app.route("/api/bugs/<bug_id>", methods=["GET"])
async def get_bug(bug_id):
    async with bugs_lock:
        bug = bugs.get(bug_id)
    if not bug:
        abort(404, "Bug not found")
    async with comments_lock:
        bug_comments = comments.get(bug_id, [])
    bug_with_comments = dict(bug)
    bug_with_comments["comments"] = bug_comments
    return jsonify(bug_with_comments)

@app.route("/api/bugs/<bug_id>/update", methods=["POST"])
@validate_request(UpdateBugRequest)  # validation last for POST (workaround issue)
async def update_bug(bug_id, data: UpdateBugRequest):
    payload = data.__dict__
    validate_bug_input(payload, update=True)
    async with bugs_lock:
        bug = bugs.get(bug_id)
        if not bug:
            abort(404, "Bug not found")
        updated = False
        if data.status and data.status != bug["status"]:
            bug["status"] = data.status; updated = True
        if data.description and data.description.strip() != bug["description"]:
            bug["description"] = data.description.strip(); updated = True
        if data.severity and data.severity != bug["severity"]:
            bug["severity"] = data.severity; updated = True
        if data.steps_to_reproduce and data.steps_to_reproduce.strip() != bug["steps_to_reproduce"]:
            bug["steps_to_reproduce"] = data.steps_to_reproduce.strip(); updated = True
        if updated:
            bug["updated_at"] = iso8601_now()
            bugs[bug_id] = bug
            logger.info(f"Bug {bug_id} updated")
    return jsonify({"bug_id": bug_id, "status": bug["status"], "updated_at": bug["updated_at"]})

@app.route("/api/bugs/<bug_id>/comments", methods=["POST"])
@validate_request(AddCommentRequest)  # validation last for POST (workaround issue)
async def add_comment(bug_id, data: AddCommentRequest):
    async with bugs_lock:
        if bug_id not in bugs:
            abort(404, "Bug not found")
    comment_id = str(uuid.uuid4())
    now = iso8601_now()
    comment = {"comment_id": comment_id, "author": data.author.strip(),
               "message": data.message.strip(), "created_at": now}
    async with comments_lock:
        comments.setdefault(bug_id, []).append(comment)
    logger.info(f"Added comment {comment_id} to bug {bug_id}")
    return jsonify({"comment_id": comment_id, "bug_id": bug_id,
                    "author": comment["author"], "message": comment["message"],
                    "created_at": now}), 201

# TODO: No external APIs specified; implement httpx.AsyncClient logic when needed.

if __name__ == "__main__":
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)