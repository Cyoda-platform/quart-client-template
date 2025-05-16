import asyncio
import logging
from datetime import datetime
from typing import Dict
from dataclasses import dataclass

import httpx
from quart import Blueprint, jsonify
from quart_schema import validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

routes_bp = Blueprint('routes', __name__)

@dataclass
class AnalyzeRequest:
    post_id: int
    email: str

async def fetch_comments(post_id: int):
    url = f"https://jsonplaceholder.typicode.com/comments?postId={post_id}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()

def analyze_comments(comments: list):
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
    # Placeholder for real email sending logic
    logger.info(f"Sending report email to {email} for post {post_id} with summary {summary}")

@routes_bp.route("/comments/analyze", methods=["POST"])
@validate_request(AnalyzeRequest)
async def analyze_comments_endpoint(data: AnalyzeRequest):
    """
    Endpoint accepts post_id and email, creates minimal entity with status 'processing',
    calls add_item with workflow function to handle processing asynchronously.
    """
    entity = {
        "post_id": data.post_id,
        "email": data.email,
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat()
    }

    try:
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="prototype",
            entity_version=ENTITY_VERSION,
            entity=entity
        )
    except Exception as e:
        logger.exception("Failed to add prototype entity: %s", e)
        return jsonify({"error": "Failed to start analysis"}), 500

    return jsonify({
        "status": "processing",
        "message": f"Analysis started and report will be sent to {data.email}",
        "entity_id": entity_id
    }), 202

@routes_bp.route("/reports/<string:post_id>", methods=["GET"])
async def get_report(post_id: str):
    try:
        report = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="prototype",
            entity_version=ENTITY_VERSION,
            technical_id=post_id
        )
    except Exception as e:
        logger.exception("Failed to retrieve report for post_id %s: %s", post_id, e)
        return jsonify({"error": f"Failed to retrieve report for post_id {post_id}"}), 500

    if not report:
        return jsonify({"error": f"No report found for post_id {post_id}"}), 404
    return jsonify(report)