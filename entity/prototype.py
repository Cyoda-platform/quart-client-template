import asyncio
import uuid
import logging
import datetime
from typing import List, Dict, Any

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request  # Using validate_request for POST endpoints
from dataclasses import dataclass

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for jobs (mock persistence)
jobs: Dict[str, Dict[str, Any]] = {}


# Data class for the analyze request body
@dataclass
class AnalyzeRequest:
    post_ids: List[int]
    email: str


# TODO: Replace with a real email sending function in production
async def send_email(recipient: str, subject: str, body: str):
    logger.info(f"Sending email to {recipient} with subject '{subject}' and body:\n{body}")
    # Simulate email sending delay
    await asyncio.sleep(0.5)


# Helper function to perform sentiment analysis (mock implementation)
def perform_sentiment_analysis(comment: str) -> str:
    # TODO: Implement real sentiment analysis
    # Placeholder: categorize everything as 'neutral' sentiment.
    return "neutral"


# Helper function to perform keyword extraction (mock implementation)
def extract_keywords(comment: str) -> List[str]:
    # TODO: Implement real keyword extraction
    # Placeholder: simply split the comment into words and return unique words.
    return list(set(comment.split()))


async def fetch_comments_for_post(post_id: int) -> List[Dict[str, Any]]:
    url = f"https://jsonplaceholder.typicode.com/posts/{post_id}/comments"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            comments = response.json()
            logger.info(f"Fetched {len(comments)} comments for post_id {post_id}")
            return comments
        except Exception as e:
            logger.exception(e)
            # Return empty list on failure
            return []


async def process_entity(job_id: str, post_ids: List[int], recipient_email: str):
    try:
        all_comments = []
        # Retrieve comments for each post id concurrently
        tasks = [fetch_comments_for_post(pid) for pid in post_ids]
        results = await asyncio.gather(*tasks)
        for comments in results:
            all_comments.extend(comments)

        # Perform analysis on the gathered comments
        total_comments = len(all_comments)
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        keywords_frequency = {}

        for comment in all_comments:
            body = comment.get("body", "")
            sentiment = perform_sentiment_analysis(body)
            sentiment_counts[sentiment] += 1

            keywords = extract_keywords(body)
            for kw in keywords:
                keywords_frequency[kw] = keywords_frequency.get(kw, 0) + 1

        # Build a plain text summary report
        report_lines = [
            f"Total Comments Analyzed: {total_comments}",
            f"Positive Comments: {sentiment_counts['positive']}",
            f"Negative Comments: {sentiment_counts['negative']}",
            f"Neutral Comments: {sentiment_counts['neutral']}",
            "",
            "Keywords Frequency:"
        ]
        for kw, freq in keywords_frequency.items():
            report_lines.append(f"- {kw}: {freq} occurrence(s)")

        report = "\n".join(report_lines)
        logger.info(f"Analysis report for job_id {job_id} created.")

        # Update the job in the mock persistence
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["report"] = report

        # Send the report via email
        await send_email(recipient_email, "Analysis Report", report)

    except Exception as e:
        logger.exception(e)
        # In a real implementation, update the job with an error status
        jobs[job_id]["status"] = "error"
        jobs[job_id]["report"] = str(e)


# Workaround for quart-schema ordering issue:
# For POST endpoints, the route decorator must be placed first, then validate_request.
@app.route("/api/analyze", methods=["POST"])
@validate_request(AnalyzeRequest)
async def analyze(data: AnalyzeRequest):
    try:
        post_ids = data.post_ids
        recipient_email = data.email

        if not post_ids or not recipient_email:
            return jsonify({"error": "post_ids and email are required fields"}), 400

        # Generate unique job_id
        job_id = str(uuid.uuid4())
        requested_at = datetime.datetime.utcnow().isoformat()

        # Store job in the local cache
        jobs[job_id] = {"status": "processing", "requestedAt": requested_at}
        logger.info(f"Job {job_id} created with post_ids {post_ids} for recipient {recipient_email}")

        # Fire and forget the processing task.
        asyncio.create_task(process_entity(job_id, post_ids, recipient_email))

        return jsonify({"job_id": job_id, "status": "processing"}), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/result/<job_id>", methods=["GET"])
async def get_result(job_id: str):
    try:
        job = jobs.get(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404

        response = {
            "job_id": job_id,
            "status": job.get("status"),
            "report": job.get("report", "")
        }
        return jsonify(response), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)