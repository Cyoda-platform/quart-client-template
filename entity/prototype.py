import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from dataclasses import dataclass

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class AnalyzeRequest:
    post_id: int
    email: str

# In-memory async-safe cache for jobs and reports
entity_jobs: Dict[str, Dict[str, Any]] = {}
reports_cache: Dict[int, Dict[str, Any]] = {}

COMMENTS_API_URL = "https://jsonplaceholder.typicode.com/comments"


async def fetch_comments(post_id: int) -> list:
    async with httpx.AsyncClient() as client:
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
        words = [w.strip(".,!?").lower() for w in c.get("body", "").split()]
        filtered_words = [w for w in words if w and w not in stopwords]
        for w in filtered_words:
            word_freq[w] = word_freq.get(w, 0) + 1
        sentiment = "positive" if len(c.get("body", "")) > 100 else "neutral"
        comment_keywords = list(set(filtered_words))[:3]
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
    logger.info(f"Sending report email to {email} for post_id {post_id} with report summary: {report['summary']}")
    await asyncio.sleep(0.1)


async def process_entity(job_id: str, data: Dict[str, Any]):
    try:
        post_id = data["post_id"]
        email = data["email"]
        comments = await fetch_comments(post_id)
        report_data = analyze_comments(comments)
        reports_cache[post_id] = {
            "post_id": post_id,
            "summary": {
                "total_comments": report_data["total_comments"],
                "sentiment_score": report_data["sentiment_score"],
                "keywords": report_data["keywords"],
            },
            "details": report_data["details"],
        }
        await send_report_email(email, post_id, reports_cache[post_id])
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["finishedAt"] = datetime.utcnow().isoformat() + "Z"
    except Exception as e:
        logger.exception(e)
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        entity_jobs[job_id]["finishedAt"] = datetime.utcnow().isoformat() + "Z"


@app.route("/api/comments/analyze", methods=["POST"])
@validate_request(AnalyzeRequest)  # issue workaround: validation last for POST
async def analyze_comments_endpoint(data: AnalyzeRequest):
    post_id = data.post_id
    email = data.email
    requested_at = datetime.utcnow().isoformat() + "Z"
    job_id = f"{post_id}-{requested_at}"
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}
    asyncio.create_task(process_entity(job_id, {"post_id": post_id, "email": email}))
    return jsonify({
        "status": "processing",
        "message": "Analysis started and email will be sent upon completion.",
        "job_id": job_id,
    }), 202


@app.route("/api/reports/<int:post_id>", methods=["GET"])
async def get_report(post_id: int):
    report = reports_cache.get(post_id)
    if not report:
        return jsonify({"error": "Report not found or still processing"}), 404
    return jsonify(report)


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)