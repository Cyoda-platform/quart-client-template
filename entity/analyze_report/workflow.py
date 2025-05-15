import asyncio
import logging
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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
    # TODO: Implement real email sending
    logger.info(f"Sending report for post_id {post_id} to {email}: {report}")

async def process_fetch_comments(entity: dict):
    post_id = entity.get("post_id")
    if isinstance(post_id, str) and post_id.isdigit():
        post_id = int(post_id)
    entity["comments"] = await fetch_comments(post_id)

async def process_analyze_comments(entity: dict):
    comments = entity.get("comments", [])
    entity["report"] = analyze_comments_sentiment(comments)

async def process_send_email(entity: dict):
    email = entity.get("email")
    post_id = entity.get("post_id")
    report = entity.get("report")
    await send_report_email(email, post_id, report)

async def process_finalize_report(entity: dict):
    report = entity.get("report", {})
    entity["status"] = "completed"
    entity["completed_at"] = datetime.utcnow().isoformat()
    entity["result_summary"] = report.get("summary")

async def process_fail(entity: dict, error: Exception):
    logger.exception("Error in process_analyze_request workflow")
    entity["status"] = "failed"
    entity["error"] = str(error)
    entity["completed_at"] = datetime.utcnow().isoformat()

async def process_analyze_request(entity: dict):
    try:
        entity["status"] = "processing"
        entity["processing_started_at"] = datetime.utcnow().isoformat()

        await process_fetch_comments(entity)
        await process_analyze_comments(entity)
        await process_send_email(entity)
        await process_finalize_report(entity)

    except Exception as e:
        await process_fail(entity, e)