from datetime import timezone, datetime
import logging
from quart import Blueprint, request, abort, jsonify
from quart_schema import validate, validate_querystring, tag, operation_id, validate_request
from app_init.app_init import BeanFactory
from dataclasses import dataclass
from typing import Dict, Any
import asyncio
import httpx

logger = logging.getLogger(__name__)
FINAL_STATES = {'FAILURE', 'SUCCESS', 'CANCELLED', 'CANCELLED_BY_USER', 'UNKNOWN', 'FINISHED'}
PROCESSING_STATE = 'PROCESSING'

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

@dataclass
class AnalyzeRequest:
    post_id: int
    email: str

# In-memory async-safe cache for jobs and reports
entity_jobs: Dict[str, Dict[str, Any]] = {}
reports_cache: Dict[str, Dict[str, Any]] = {}

COMMENTS_API_URL = "https://jsonplaceholder.typicode.com/comments"


async def fetch_comments(post_id: int) -> list:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(COMMENTS_API_URL, params={"postId": post_id})
        resp.raise_for_status()
        return resp.json()


def analyze_comments(comments: list) -> Dict[str, Any]:
    stopwords = {
        "the", "and", "is", "in", "to", "of", "a", "it", "that", "on", "for",
        "with", "as", "this", "was", "but", "be", "at", "by", "or", "an"
    }
    word_freq: Dict[str, int] = {}
    details = []
    for c in comments:
        body = c.get("body", "")
        words = [w.strip(".,!?").lower() for w in body.split()]
        filtered_words = [w for w in words if w and w not in stopwords]
        for w in filtered_words:
            word_freq[w] = word_freq.get(w, 0) + 1
        sentiment = "positive" if len(body) > 100 else "neutral"
        comment_keywords = list(dict.fromkeys(filtered_words))[:3]  # preserve order, unique
        details.append({
            "comment_id": c.get("id"),
            "sentiment": sentiment,
            "keywords": comment_keywords,
        })
    total_comments = len(comments)
    avg_length = sum(len(c.get("body", "")) for c in comments) / total_comments if total_comments else 0
    sentiment_score = min(max(avg_length / 200, 0), 1)
    top_keywords = sorted(word_freq, key=word_freq.get, reverse=True)[:3]
    return {
        "total_comments": total_comments,
        "sentiment_score": sentiment_score,
        "keywords": top_keywords,
        "details": details,
    }


async def send_report_email(email: str, post_id: int, report: Dict[str, Any]):
    # Simulated email sending; in production, replace with real email sending logic
    logger.info(f"Sending report email to {email} for post_id {post_id} with report summary: {report['summary']}")
    await asyncio.sleep(0.1)


@routes_bp.route("/api/comments/analyze", methods=["POST"])
@validate_request(AnalyzeRequest)
async def analyze_comments_endpoint(data: AnalyzeRequest):
    entity_data = {"post_id": data.post_id, "email": data.email}
    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="analyze_request",
            entity_version=None,
            entity=entity_data
        )
        job_id = entity_data.get("job_id", None)
        # job_id may not be set immediately because workflow runs async before persistence
        # However, per spec workflow is awaited before persistence so job_id should be present
        return jsonify({
            "status": "processing",
            "message": "Analysis started and email will be sent upon completion.",
            "job_id": job_id,
            "id": id
        }), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to start analysis"}), 500


@routes_bp.route("/api/reports/<string:post_id>", methods=["GET"])
async def get_report(post_id: str):
    report = reports_cache.get(post_id)
    if not report:
        return jsonify({"error": "Report not found or still processing"}), 404
    return jsonify(report)