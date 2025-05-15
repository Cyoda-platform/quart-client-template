import asyncio
import logging
from datetime import datetime
from typing import Dict
from dataclasses import dataclass

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class AnalyzeRequest:
    post_id: int
    email: str

# In-memory async-safe storage for reports and job statuses
class Storage:
    def __init__(self):
        self._reports: Dict[int, dict] = {}
        self._jobs: Dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def set_job(self, job_id: str, data: dict):
        async with self._lock:
            self._jobs[job_id] = data

    async def get_job(self, job_id: str):
        async with self._lock:
            return self._jobs.get(job_id)

    async def set_report(self, post_id: int, report: dict):
        async with self._lock:
            self._reports[post_id] = report

    async def get_report(self, post_id: int):
        async with self._lock:
            return self._reports.get(post_id)

storage = Storage()

def analyze_comments_sentiment(comments):
    positive_keywords = {"good", "great", "positive", "love", "excellent"}
    negative_keywords = {"bad", "worst", "negative", "hate", "terrible"}

    positive = negative = neutral = 0

    for comment in comments:
        body = comment.get("body", "").lower()
        if any(word in body for word in positive_keywords):
            positive += 1
        elif any(word in body for word in negative_keywords):
            negative += 1
        else:
            neutral += 1

    if positive > max(negative, neutral):
        summary = "Sentiment analysis indicates mostly positive comments."
    elif negative > max(positive, neutral):
        summary = "Sentiment analysis indicates mostly negative comments."
    else:
        summary = "Sentiment analysis indicates neutral or mixed comments."

    return {"summary": summary, "details": {"positive": positive, "negative": negative, "neutral": neutral}}

async def fetch_comments(post_id: int):
    url = f"https://jsonplaceholder.typicode.com/comments?postId={post_id}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()

async def send_report_email(email: str, post_id: int, report: dict):
    # TODO: Implement real email sending
    logger.info(f"Sending report for post_id {post_id} to {email}: {report}")

async def process_entity(job_id: str, post_id: int, email: str):
    try:
        comments = await fetch_comments(post_id)
        report = analyze_comments_sentiment(comments)
        await storage.set_report(post_id, report)
        await send_report_email(email, post_id, report)
        await storage.set_job(job_id, {"status": "completed", "completedAt": datetime.utcnow().isoformat()})
    except Exception as e:
        logger.exception(e)
        await storage.set_job(job_id, {"status": "failed", "error": str(e), "completedAt": datetime.utcnow().isoformat()})

@app.route("/comments/analyze", methods=["POST"])
@validate_request(AnalyzeRequest)  # workaround: validate_request must follow route decorator for POST due to quart-schema defect
async def analyze_comments(data: AnalyzeRequest):
    post_id = data.post_id
    email = data.email
    job_id = f"{post_id}-{datetime.utcnow().timestamp()}"
    await storage.set_job(job_id, {"status": "processing", "requestedAt": datetime.utcnow().isoformat()})
    asyncio.create_task(process_entity(job_id, post_id, email))
    return jsonify({
        "status": "processing",
        "message": "Analysis started and report will be sent to the provided email.",
        "job_id": job_id
    }), 202

@app.route("/reports/<int:post_id>", methods=["GET"])
async def get_report(post_id):
    report = await storage.get_report(post_id)
    if not report:
        return jsonify({"error": "Report not found for given post_id"}), 404
    return jsonify({"post_id": post_id, "report": report})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)