from dataclasses import dataclass
import uuid
from datetime import datetime
from typing import Optional

import logging
from quart import Blueprint, jsonify, request, abort
from quart_schema import validate_request, validate_querystring

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

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

@routes_bp.route("/api/bugs", methods=["POST"])
@validate_request(CreateBugRequest)
async def create_bug(data: CreateBugRequest):
    bug_data = data.__dict__
    validate_bug_input(bug_data)
    try:
        bug_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="bug",
            entity_version=ENTITY_VERSION,
            entity=bug_data
        )
        logger.info(f"Created bug {bug_id}")
        return jsonify({"bug_id": bug_id}), 201
    except Exception as e:
        logger.exception(e)
        abort(500, "Failed to create bug")

@routes_bp.route("/api/bugs", methods=["GET"])
@validate_querystring(ListBugsQuery)
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

    try:
        all_bugs = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="bug",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.exception(e)
        abort(500, "Failed to retrieve bugs")

    def bug_matches(bug):
        if status_filter and bug.get("status") != status_filter:
            return False
        if severity_filter and bug.get("severity") != severity_filter:
            return False
        if search and search not in bug.get("title", "").lower() and search not in bug.get("description", "").lower():
            return False
        return True

    filtered = list(filter(bug_matches, all_bugs))
    reverse = sort_order == "desc"
    if sort_by in {"created_at", "severity", "status"}:
        if sort_by == "severity":
            severity_order = {"low": 0, "medium": 1, "high": 2}
            def key_func(b): return severity_order.get(b.get("severity"), -1)
        else:
            def key_func(b): return b.get(sort_by, "")
        filtered.sort(key=key_func, reverse=reverse)

    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    paged = filtered[start:end]
    bugs_list = [
        {"bug_id": b.get("bug_id"), "title": b.get("title"), "status": b.get("status"),
         "severity": b.get("severity"), "created_at": b.get("created_at")}
        for b in paged
    ]
    return jsonify({"total": total, "page": page, "page_size": page_size, "bugs": bugs_list})

@routes_bp.route("/api/bugs/<bug_id>", methods=["GET"])
async def get_bug(bug_id):
    try:
        bug = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="bug",
            entity_version=ENTITY_VERSION,
            technical_id=bug_id,
        )
        if not bug:
            abort(404, "Bug not found")
    except Exception as e:
        logger.exception(e)
        abort(500, "Failed to retrieve bug")

    bug_with_comments = dict(bug)
    if hasattr(routes_bp, 'comments'):
        bug_with_comments["comments"] = routes_bp.comments.get(bug_id, [])
    else:
        bug_with_comments["comments"] = []
    return jsonify(bug_with_comments)

@routes_bp.route("/api/bugs/<bug_id>/update", methods=["POST"])
@validate_request(UpdateBugRequest)
async def update_bug(bug_id, data: UpdateBugRequest):
    payload = data.__dict__
    validate_bug_input(payload, update=True)
    try:
        existing_bug = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="bug",
            entity_version=ENTITY_VERSION,
            technical_id=bug_id,
        )
        if not existing_bug:
            abort(404, "Bug not found")

        # Merge update fields into existing bug
        updated_bug = dict(existing_bug)
        for k, v in payload.items():
            if v is not None:
                updated_bug[k] = v

        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="bug",
            entity_version=ENTITY_VERSION,
            entity=updated_bug,
            technical_id=bug_id,
            meta={}
        )
        logger.info(f"Bug {bug_id} updated")
        return jsonify({"bug_id": bug_id, "updated_at": updated_bug.get("updated_at")})

    except Exception as e:
        logger.exception(e)
        abort(500, "Failed to update bug")

@routes_bp.route("/api/bugs/<bug_id>/comments", methods=["POST"])
@validate_request(AddCommentRequest)
async def add_comment(bug_id, data: AddCommentRequest):
    try:
        bug = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="bug",
            entity_version=ENTITY_VERSION,
            technical_id=bug_id,
        )
        if not bug:
            abort(404, "Bug not found")
    except Exception as e:
        logger.exception(e)
        abort(500, "Failed to verify bug existence")

    comment_id = str(uuid.uuid4())
    now = iso8601_now()
    comment = {
        "comment_id": comment_id,
        "author": data.author.strip(),
        "message": data.message.strip(),
        "created_at": now
    }
    if not hasattr(routes_bp, 'comments'):
        routes_bp.comments = {}
    routes_bp.comments.setdefault(bug_id, []).append(comment)
    logger.info(f"Added comment {comment_id} to bug {bug_id}")
    return jsonify({
        "comment_id": comment_id,
        "bug_id": bug_id,
        "author": comment["author"],
        "message": comment["message"],
        "created_at": now
    }), 201