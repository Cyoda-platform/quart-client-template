import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

entity_jobs: Dict[str, Dict[str, Any]] = {}
reports_cache: Dict[str, Dict[str, Any]] = {}

COMMENTS_API_URL = "https://jsonplaceholder.typicode.com/comments"


async def fetch_comments(post_id: int) -> list:
    async with httpx.AsyncClient() as client:
        resp = await client.get(COMMENTS_API_URL, params={"postId": post_id})
        resp.raise_for_status()
        return resp.json()


def analyze_comments(comments: list) -> Dict[str, Any]:
    stopwords = {
        "the", "and", "is", "in", "to", "of", "a", "it", "that", "on", "for",
        "with", "as", "this", "was", "but", "be", "at", "by", "or", "an"
    }
    word_freq: Dict[str, int] = {}
    details = []

    for c in comments:
        words = [w.strip(".,!?").lower() for w in c.get("body", "").split()]
        filtered_words = [w for w in words if w and w not in stopwords]
        for w in filtered_words:
            word_freq[w] = word_freq.get(w, 0) + 1
        sentiment = "positive" if len(c.get("body", "")) > 100 else "neutral"
        comment_keywords = list(set(filtered_words))[:3]
        details.append({
            "comment_id": c.get("id"),
            "sentiment": sentiment,
            "keywords": comment_keywords,
        })

    total_comments = len(comments)
    avg_length = sum(len(c.get("body", "")) for c in comments) / total_comments if total_comments else 0
    sentiment_score = min(max(avg_length / 200, 0), 1)
    top_keywords = sorted(word_freq, key=word_freq.get, reverse=True)[:3]

    return {
        "total_comments": total_comments,
        "sentiment_score": sentiment_score,
        "keywords": top_keywords,
        "details": details,
    }


async def send_report_email(email: str, post_id: int, report: Dict[str, Any]):
    logger.info(f"Sending report email to {email} for post_id {post_id} with report summary: {report['summary']}")
    await asyncio.sleep(0.1)


async def process_fetch_comments(entity: Dict[str, Any]) -> None:
    post_id = entity.get("post_id")
    comments = await fetch_comments(post_id)
    entity["comments"] = comments  # Store temporarily for next steps


async def process_analyze_comments(entity: Dict[str, Any]) -> None:
    comments = entity.get("comments", [])
    report_data = analyze_comments(comments)
    entity["report_data"] = report_data


async def process_cache_report(entity: Dict[str, Any]) -> None:
    post_id = entity.get("post_id")
    report_data = entity.get("report_data")
    reports_cache[str(post_id)] = {
        "post_id": post_id,
        "summary": {
            "total_comments": report_data["total_comments"],
            "sentiment_score": report_data["sentiment_score"],
            "keywords": report_data["keywords"],
        },
        "details": report_data["details"],
    }


async def process_send_email(entity: Dict[str, Any]) -> None:
    post_id = entity.get("post_id")
    email = entity.get("email")
    report = reports_cache.get(str(post_id))
    if report:
        try:
            await send_report_email(email, post_id, report)
        except Exception as e:
            logger.error(f"Failed to send report email to {email} for post_id {post_id}: {e}")


async def process_update_job_status(entity: Dict[str, Any], status: str, error: str = None) -> None:
    job_id = entity.get("job_id")
    if job_id and job_id in entity_jobs:
        entity_jobs[job_id]["status"] = status
        entity_jobs[job_id]["finishedAt"] = datetime.utcnow().isoformat() + "Z"
        if error:
            entity_jobs[job_id]["error"] = error


async def process_analyze_request(entity: Dict[str, Any]) -> Dict[str, Any]:
    post_id = entity.get("post_id")
    email = entity.get("email")

    if post_id is None or email is None:
        entity["status"] = "failed"
        entity["error"] = "Missing required post_id or email"
        return entity

    job_id = f"{post_id}-{datetime.utcnow().isoformat()}Z"
    entity["job_id"] = job_id
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat() + "Z"}

    try:
        await process_fetch_comments(entity)
    except Exception as e:
        logger.exception(f"Failed to fetch comments for post_id {post_id}: {e}")
        await process_update_job_status(entity, "failed", f"Failed to fetch comments: {str(e)}")
        entity["status"] = "failed"
        entity["error"] = str(e)
        return entity

    try:
        await process_analyze_comments(entity)
    except Exception as e:
        logger.exception(f"Failed to analyze comments for post_id {post_id}: {e}")
        await process_update_job_status(entity, "failed", f"Failed to analyze comments: {str(e)}")
        entity["status"] = "failed"
        entity["error"] = str(e)
        return entity

    await process_cache_report(entity)

    try:
        await process_send_email(entity)
    except Exception:
        # Already logged inside process_send_email, do not fail job on email errors
        pass

    await process_update_job_status(entity, "completed")

    entity["requestedAt"] = entity_jobs[job_id]["requestedAt"]
    entity["status"] = "completed"
    entity["report_summary"] = reports_cache[str(post_id)]["summary"]

    # Clean temporary keys
    entity.pop("comments", None)
    entity.pop("report_data", None)

    return entity