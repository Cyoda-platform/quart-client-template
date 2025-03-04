#!/usr/bin/env python3
import asyncio
import uuid
import logging
import datetime
from typing import List, Dict, Any

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request  # Using validate_request for POST endpoints
from dataclasses import dataclass

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Data class for the analyze request body
@dataclass
class AnalyzeRequest:
    post_ids: List[int]
    email: str

# TODO: Replace with a real email sending function in production
async def send_email(recipient: str, subject: str, body: str):
    logger.info(f"Sending email to {recipient} with subject '{subject}' and body:\n{body}")
    await asyncio.sleep(0.5)

# Helper function to perform sentiment analysis (mock implementation)
def perform_sentiment_analysis(comment: str) -> str:
    return "neutral"

# Helper function to perform keyword extraction (mock implementation)
def extract_keywords(comment: str) -> List[str]:
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
            return []

# Workflow function for job entity.
# This function is applied to the job entity asynchronously before it is persisted.
# It performs the analysis and sends the report email. Any changes to the entity dictionary
# will be persisted.
async def process_job(entity: Dict[str, Any]) -> Dict[str, Any]:
    # Add metadata about the workflow
    entity["workflow_applied"] = True
    entity["workflow_timestamp"] = datetime.datetime.utcnow().isoformat()
    
    post_ids = entity.get("post_ids", [])
    recipient_email = entity.get("recipient_email", "")
    
    if not post_ids or not recipient_email:
        entity["status"] = "error"
        entity["report"] = "Missing post_ids or recipient_email."
        return entity

    # Fetch comments concurrently for all provided post IDs
    all_comments = []
    tasks = [fetch_comments_for_post(pid) for pid in post_ids]
    results = await asyncio.gather(*tasks)
    for comments in results:
        all_comments.extend(comments)
    
    # Analyze the fetched comments
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
    
    # Compose a report based on the analysis
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
    
    # Update the entity with the analysis result
    entity["status"] = "completed"
    entity["report"] = report

    # Send the analysis report via email (fire-and-forget is acceptable since workflow supports async code)
    await send_email(recipient_email, "Analysis Report", report)
    
    return entity

@app.route("/api/analyze", methods=["POST"])
@validate_request(AnalyzeRequest)
async def analyze(data: AnalyzeRequest):
    try:
        post_ids = data.post_ids
        recipient_email = data.email

        if not post_ids or not recipient_email:
            return jsonify({"error": "post_ids and email are required fields"}), 400

        requested_at = datetime.datetime.utcnow().isoformat()
        job_data = {
            "status": "processing",
            "requestedAt": requested_at,
            "post_ids": post_ids,
            "recipient_email": recipient_email
        }

        # The workflow function process_job will be applied to the entity before persisting.
        # All asynchronous tasks (analysis, sending email, etc.) are executed inside the workflow.
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,  # always use this constant
            entity=job_data,
            workflow=process_job
        )
        logger.info(f"Job {job_id} created with post_ids {post_ids} for recipient {recipient_email}")

        return jsonify({"job_id": job_id, "status": "completed"}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": str(e)}), 500

@app.route("/api/result/<job_id>", methods=["GET"])
async def get_result(job_id: str):
    try:
        job = await entity_service.get_item(
            token=cyoda_token,
            entity_model="job",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )

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