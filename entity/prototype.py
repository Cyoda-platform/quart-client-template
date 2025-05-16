```python
import asyncio
import logging
from datetime import datetime
from typing import Dict

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

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
    # For prototype: simple counts of comments and dummy sentiment classification
    total = len(comments)
    positive = 0
    negative = 0
    neutral = 0

    for c in comments:
        body = c.get("body", "").lower()
        # Very naive sentiment: presence of "error", "pain", "bad" → negative, "good", "great", "love" → positive
        if any(word in body for word in ["error", "pain", "bad"]):
            negative += 1
        elif any(word in body for word in ["good", "great", "love"]):
            positive += 1
        else:
            neutral += 1

    return {
        "total_comments": total,
        "positive": positive,
        "negative": negative,
        "neutral": neutral,
    }


async def send_report_email(email: str, post_id: int, summary: dict):
    # TODO: Implement real email sending.
    # Prototype: just log the action.
    logger.info(f"Sending report email to {email} for post {post_id} with summary {summary}")


async def process_entity(job_id: str, post_id: int, email: str):
    try:
        comments = await fetch_comments(post_id)
        summary = analyze_comments(comments)
        # Store report in cache
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
async def analyze_comments_endpoint():
    data = await request.get_json(force=True)
    post_id = data.get("post_id")
    email = data.get("email")

    if not isinstance(post_id, int) or not email:
        return jsonify({"error": "Invalid request, 'post_id' (int) and 'email' (str) required"}), 400

    job_id = f"job_{datetime.utcnow().timestamp()}"
    requested_at = datetime.utcnow().isoformat()
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}

    # Fire and forget background task
    asyncio.create_task(process_entity(job_id, post_id, email))

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
```
