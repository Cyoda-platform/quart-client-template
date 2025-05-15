import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass

import httpx
from quart import Blueprint, jsonify
from quart_schema import validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

@dataclass
class AnalyzeRequest:
    post_id: int
    email: str

async def fetch_comments(post_id: int):
    url = f"https://jsonplaceholder.typicode.com/comments?postId={post_id}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()

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

async def send_report_email(email: str, post_id: int, report: dict):
    # TODO: Replace with real email sending logic
    logger.info(f"Sending report for post_id {post_id} to {email}: {report}")

async def process_analyze_request(entity: dict):
    try:
        post_id = entity["post_id"]
        if isinstance(post_id, str) and post_id.isdigit():
            post_id = int(post_id)
        email = entity["email"]

        entity["status"] = "processing"
        entity["processing_started_at"] = datetime.utcnow().isoformat()

        comments = await fetch_comments(post_id)
        report = analyze_comments_sentiment(comments)
        await send_report_email(email, post_id, report)

        report_entity = {
            "post_id": str(post_id),
            "report": report,
            "email": email,
            "created_at": datetime.utcnow().isoformat(),
        }
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="analyze_report",
            entity_version=ENTITY_VERSION,
            entity=report_entity,
            workflow=None
        )

        entity["status"] = "completed"
        entity["completed_at"] = datetime.utcnow().isoformat()
        entity["result_summary"] = report.get("summary")

    except Exception as e:
        logger.exception("Error in process_analyze_request workflow")
        entity["status"] = "failed"
        entity["error"] = str(e)
        entity["completed_at"] = datetime.utcnow().isoformat()

@routes_bp.route("/comments/analyze", methods=["POST"])
@validate_request(AnalyzeRequest)
async def analyze_comments(data: AnalyzeRequest):
    entity = {
        "post_id": data.post_id,
        "email": data.email,
        "created_at": datetime.utcnow().isoformat(),
        "status": "requested",
    }

    entity_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="analyze_request",
        entity_version=ENTITY_VERSION,
        entity=entity,
        workflow=None
    )

    return jsonify({
        "status": "processing",
        "message": "Analysis started and report will be sent to the provided email.",
        "entity_id": entity_id,
    }), 202

@routes_bp.route("/reports/<string:post_id>", methods=["GET"])
async def get_report(post_id):
    try:
        item = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="analyze_report",
            entity_version=ENTITY_VERSION,
            technical_id=post_id
        )
        if not item:
            return jsonify({"error": "Report not found for given post_id"}), 404
        return jsonify({"post_id": post_id, "report": item.get("report")})
    except Exception as e:
        logger.exception("Failed to retrieve report")
        return jsonify({"error": "Failed to retrieve report"}), 500