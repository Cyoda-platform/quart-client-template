from datetime import datetime, timezone
import logging
from quart import Blueprint, request, jsonify
from quart_schema import validate_request
import uuid
from dataclasses import dataclass
from typing import Optional, Dict, Any

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

entity_name = "report"  # underscore lowercase

@dataclass
class AnalyzeBooksRequest:
    triggeredBy: str
    date: Optional[str] = None

def parse_iso_date(date_str: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(date_str.rstrip("Z")).replace(tzinfo=timezone.utc)
    except Exception:
        logger.exception(f"Failed to parse date: {date_str}")
        return None

@routes_bp.route("/analyze-books", methods=["POST"])
@validate_request(AnalyzeBooksRequest)
async def analyze_books(data: AnalyzeBooksRequest):
    triggered_by = data.triggeredBy
    requested_at = data.date or datetime.now(timezone.utc).isoformat()
    job_id = str(uuid.uuid4())

    initial_entity = {
        "reportId": job_id,
        "status": "processing",
        "requestedAt": requested_at,
        "triggeredBy": triggered_by,
    }

    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=initial_entity
        )
    except Exception as e:
        logger.exception(f"Failed to add initial report status for job {job_id}: {e}")
        return jsonify({"status": "error", "message": "Failed to initiate analysis job."}), 500

    return jsonify({
        "status": "success",
        "message": "Book data analysis started.",
        "reportId": job_id,
    })

@routes_bp.route("/reports/<report_id>", methods=["GET"])
async def get_report(report_id):
    try:
        report = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            technical_id=report_id
        )
    except Exception as e:
        logger.exception(f"Failed to get report {report_id}: {e}")
        return jsonify({"error": "Report not found"}), 404

    if not report:
        return jsonify({"error": "Report not found"}), 404
    if report.get("status") == "processing":
        return jsonify({"status": "processing"}), 202
    if report.get("status") == "failed":
        return jsonify({"status": "failed", "error": report.get("error")}), 500
    return jsonify(report)