import asyncio
import uuid
import logging
import datetime
from typing import List, Dict, Any

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request  # Using validate_request for POST endpoints
from dataclasses import dataclass

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

logger = logging.getLogger(__name__)

async def send_email(recipient: str, subject: str, body: str):
    # Fire-and-forget email sending (simulated)
    logger.info(f"Sending email to {recipient} with subject '{subject}' and body:\n{body}")
    await asyncio.sleep(0.5)

def perform_sentiment_analysis(comment: str) -> str:
    # In a real scenario, perform natural language processing to determine sentiment.
    return "neutral"

def extract_keywords(comment: str) -> List[str]:
    # In a real scenario, apply text processing techniques to extract significant keywords.
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

# Business logic functions (each modifies the entity directly)

async def process_update_metadata(entity: dict):
    # Update workflow metadata
    entity["workflow_applied"] = True
    entity["workflow_timestamp"] = datetime.datetime.utcnow().isoformat()

async def process_validate_entity(entity: dict):
    # Validate required fields in the entity
    post_ids = entity.get("post_ids", [])
    recipient_email = entity.get("recipient_email", "")
    if not post_ids or not recipient_email:
        entity["status"] = "error"
        entity["report"] = "Missing post_ids or recipient_email."

async def process_analyze_comments(entity: dict):
    # Analyze comments stored in entity["all_comments"]
    all_comments = entity.get("all_comments", [])
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

    # Compose a detailed analysis report.
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

    entity["report"] = report
    entity["status"] = "completed"

async def process_send_email(entity: dict):
    # Send email with the analysis report
    recipient_email = entity.get("recipient_email", "")
    report = entity.get("report", "")
    if recipient_email and report:
        await send_email(recipient_email, "Analysis Report", report)