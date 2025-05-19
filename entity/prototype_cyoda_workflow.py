import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from dataclasses import dataclass

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

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


async def process_analyze_request(entity: Dict[str, Any]) -> Dict[str, Any]:
    """
    Workflow function applied asynchronously before persisting analyze_request entity.
    Executes full processing: fetch comments, analyze, cache report, send email, update job status.
    """
    post_id = entity.get("post_id")
    email = entity.get("email")

    if post_id is None or email is None:
        entity["status"] = "failed"
        entity["error"] = "Missing required post_id or email"
        return entity

    job_id = f"{post_id}-{datetime.utcnow().isoformat()}Z"

    # Initialize job status
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat() + "Z"}

    try:
        comments = await fetch_comments(post_id)
    except Exception as e:
        logger.exception(f"Failed to fetch comments for post_id {post_id}: {e}")
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = f"Failed to fetch comments: {str(e)}"
        entity_jobs[job_id]["finishedAt"] = datetime.utcnow().isoformat() + "Z"
        entity["job_id"] = job_id
        entity["status"] = "failed"
        entity["error"] = str(e)
        return entity

    try:
        report_data = analyze_comments(comments)
    except Exception as e:
        logger.exception(f"Failed to analyze comments for post_id {post_id}: {e}")
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = f"Failed to analyze comments: {str(e)}"
        entity_jobs[job_id]["finishedAt"] = datetime.utcnow().isoformat() + "Z"
        entity["job_id"] = job_id
        entity["status"] = "failed"
        entity["error"] = str(e)
        return entity

    # Cache report data safely
    reports_cache[str(post_id)] = {
        "post_id": post_id,
        "summary": {
            "total_comments": report_data["total_comments"],
            "sentiment_score": report_data["sentiment_score"],
            "keywords": report_data["keywords"],
        },
        "details": report_data["details"],
    }

    try:
        await send_report_email(email, post_id, reports_cache[str(post_id)])
    except Exception as e:
        logger.error(f"Failed to send report email to {email} for post_id {post_id}: {e}")
        # Email failure does not fail the job; just log it

    # Update job status to completed
    entity_jobs[job_id]["status"] = "completed"
    entity_jobs[job_id]["finishedAt"] = datetime.utcnow().isoformat() + "Z"

    # Add job info and report summary to entity for persistence
    entity["job_id"] = job_id
    entity["requestedAt"] = entity_jobs[job_id]["requestedAt"]
    entity["status"] = "completed"
    entity["report_summary"] = reports_cache[str(post_id)]["summary"]

    return entity


@app.route("/api/comments/analyze", methods=["POST"])
@validate_request(AnalyzeRequest)
async def analyze_comments_endpoint(data: AnalyzeRequest):
    entity_data = {"post_id": data.post_id, "email": data.email}
    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="analyze_request",
            entity_version=ENTITY_VERSION,
            entity=entity_data,
            workflow=process_analyze_request
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


@app.route("/api/reports/<string:post_id>", methods=["GET"])
async def get_report(post_id: str):
    report = reports_cache.get(post_id)
    if not report:
        return jsonify({"error": "Report not found or still processing"}), 404
    return jsonify(report)


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)