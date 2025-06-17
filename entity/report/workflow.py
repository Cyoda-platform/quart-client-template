import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_report(entity: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"Workflow process_report started for reportId: {entity.get('reportId')}")
    try:
        await process_fetch_books(entity)
        process_analyze_books(entity)
        await process_send_email(entity)
        entity['status'] = "completed"
        entity['generatedOn'] = datetime.now(timezone.utc).isoformat()
        logger.info(f"Workflow process_report completed successfully for reportId: {entity.get('reportId')}")
    except Exception as e:
        logger.exception(f"Error in workflow process_report for reportId {entity.get('reportId')}: {e}")
        entity['status'] = "failed"
        entity['error'] = str(e)
    entity['workflowAppliedAt'] = datetime.now(timezone.utc).isoformat()
    return entity

async def process_fetch_books(entity: Dict[str, Any]) -> None:
    from httpx import AsyncClient
    FAKE_REST_API_BOOKS_URL = "https://fakerestapi.azurewebsites.net/api/v1/Books"
    async with AsyncClient() as client:
        resp = await client.get(FAKE_REST_API_BOOKS_URL)
        resp.raise_for_status()
        entity['books'] = resp.json()

def process_analyze_books(entity: Dict[str, Any]) -> None:
    from datetime import datetime, timezone
    books = entity.get('books', [])
    total_page_count = 0
    publication_dates = []
    for book in books:
        page_count = book.get("pageCount", 0) or 0
        total_page_count += page_count
        publish_date_str = book.get("publishDate")
        try:
            publish_date = datetime.fromisoformat(publish_date_str.rstrip("Z")).replace(tzinfo=timezone.utc)
        except Exception:
            publish_date = None
        if publish_date:
            publication_dates.append(publish_date)
    earliest = min(publication_dates).date().isoformat() if publication_dates else None
    latest = max(publication_dates).date().isoformat() if publication_dates else None
    sorted_books = sorted(books, key=lambda b: b.get("pageCount", 0) or 0, reverse=True)
    popular_titles = [
        {
            "id": b.get("id"),
            "title": b.get("title"),
            "description": b.get("description"),
            "excerpt": b.get("excerpt"),
            "pageCount": b.get("pageCount"),
            "publishDate": b.get("publishDate"),
        }
        for b in sorted_books[:3]
    ]
    summary = (
        f"Analyzed {len(books)} books with a total of {total_page_count} pages. "
        f"Publication dates range from {earliest} to {latest}. "
        f"Top popular titles are based on highest page counts."
    )
    entity['totalBooks'] = len(books)
    entity['totalPageCount'] = total_page_count
    entity['publicationDateRange'] = {"earliest": earliest, "latest": latest}
    entity['popularTitles'] = popular_titles
    entity['summary'] = summary

async def process_send_email(entity: Dict[str, Any]) -> None:
    # TODO: Replace with real email sending logic
    logger.info(f"Sending email report to analytics@example.com:\n{entity.get('summary')}")
    await asyncio.sleep(0.1)