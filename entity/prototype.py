import asyncio
import logging
from datetime import datetime
from typing import Dict
from dataclasses import dataclass

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class AnalyzeRequest:
    post_id: int
    email: str

# In-memory cache for reports keyed by post_id
reports_cache: Dict[int, dict] = {}
entity_jobs: Dict[str, dict] = {}

async def fetch_comments(post_id: int):
    url = f"https://jsonplaceholder.typicode.com/comments?postId={post_id}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()

def analyze_comments(comments: list):
    # TODO: Replace this placeholder analysis with real sentiment or keyword analysis
    total = len(comments)
    positive = negative = neutral = 0
    for c in comments:
        body = c.get("body", "").lower()
        if any(word in body for word in ["error", "pain", "bad"]):
            negative += 1
        elif any(word in body for word in ["good", "great", "love"]):
            positive += 1
        else:
            neutral += 1
    return {"total_comments": total, "positive": positive, "negative": negative, "neutral": neutral}

async def send_report_email(email: str, post_id: int, summary: dict):
    # TODO: Implement real email sending.
    logger.info(f"Sending report email to {email} for post {post_id} with summary {summary}")

async def process_entity(job_id: str, post_id: int, email: str):
    try:
        comments = await fetch_comments(post_id)
        summary = analyze_comments(comments)
        reports_cache[post_id] = {
            "post_id": post_id,
            "summary": summary,
            "detailed_report_url": f"https://example.com/report_post_{post_id}.pdf"  # TODO: generate real report URL
        }
        await send_report_email(email, post_id, summary)
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
        logger.info(f"Job {job_id} completed successfully.")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        logger.exception(e)

@app.route("/comments/analyze", methods=["POST"])
@validate_request(AnalyzeRequest)  # workaround: validation last for POST due to validate_request defect
async def analyze_comments_endpoint(data: AnalyzeRequest):
    post_id = data.post_id
    email = data.email
    job_id = f"job_{datetime.utcnow().timestamp()}"
    requested_at = datetime.utcnow().isoformat()
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}
    asyncio.create_task(process_entity(job_id, post_id, email))  # fire-and-forget
    return jsonify({
        "status": "processing",
        "message": f"Analysis started and report will be sent to {email}",
        "job_id": job_id
    }), 202

@app.route("/reports/<int:post_id>", methods=["GET"])
async def get_report(post_id: int):
    report = reports_cache.get(post_id)
    if not report:
        return jsonify({"error": f"No report found for post_id {post_id}"}), 404
    return jsonify(report)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)