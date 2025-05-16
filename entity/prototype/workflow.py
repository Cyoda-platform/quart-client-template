import asyncio
import logging
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def fetch_comments(post_id):
    url = f"https://jsonplaceholder.typicode.com/comments?postId={post_id}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()

def analyze_comments(comments):
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

async def send_report_email(email, post_id, summary):
    # TODO: Implement real email sending.
    logger.info(f"Sending report email to {email} for post {post_id} with summary {summary}")

async def process_fetch_comments(entity):
    post_id = entity.get("post_id")
    if post_id is None:
        raise ValueError("Entity must contain 'post_id'")
    comments = await fetch_comments(post_id)
    entity['comments'] = comments

def process_analyze_comments(entity):
    comments = entity.get('comments', [])
    summary = analyze_comments(comments)
    entity['summary'] = summary

async def process_send_email(entity):
    email = entity.get("email")
    post_id = entity.get("post_id")
    summary = entity.get("summary")
    if email is None or post_id is None or summary is None:
        raise ValueError("Entity missing required fields for sending email")
    await send_report_email(email, post_id, summary)

async def process_prototype(entity: dict):
    """
    Workflow orchestration only - no business logic here.
    """
    try:
        await process_fetch_comments(entity)
        process_analyze_comments(entity)
        entity['detailed_report_url'] = f"https://example.com/report_post_{entity.get('post_id')}.pdf"
        await process_send_email(entity)
        entity['status'] = "completed"
        entity['processedAt'] = datetime.utcnow().isoformat()
        logger.info(f"Workflow processing for prototype entity with post_id {entity.get('post_id')} completed successfully.")
    except httpx.RequestError as e:
        entity['status'] = "failed"
        entity['error'] = f"Network error during comment fetch: {str(e)}"
        logger.exception("Network error in process_prototype workflow: %s", e)
    except Exception as e:
        entity['status'] = "failed"
        entity['error'] = str(e)
        logger.exception("Error in process_prototype workflow: %s", e)