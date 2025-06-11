import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ANALYTICS_TEAM_EMAIL = "analytics-team@example.com"  # TODO: Replace with real email or config
FAKE_REST_API_BOOKS_URL = "https://fakerestapi.azurewebsites.net/api/v1/Books"

async def fetch_books() -> Optional[Dict[str, Any]]:
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(FAKE_REST_API_BOOKS_URL)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.exception(f"Failed to fetch books from external API: {e}")
            return None

def analyze_books(books: list) -> Dict[str, Any]:
    if not books:
        return {
            "totalBooks": 0,
            "totalPageCount": 0,
            "publicationDateRange": {"earliest": None, "latest": None},
            "popularTitles": [],
        }
    total_books = len(books)
    total_page_count = sum(book.get("pageCount", 0) for book in books)
    dates = []
    for book in books:
        pd = book.get("publishDate")
        if pd:
            try:
                dt = datetime.fromisoformat(pd.rstrip("Z"))
                dates.append(dt.date())
            except Exception:
                pass
    if dates:
        earliest = min(dates).isoformat()
        latest = max(dates).isoformat()
    else:
        earliest = None
        latest = None
    popular_books = sorted(books, key=lambda b: b.get("pageCount", 0), reverse=True)[:5]
    popular_titles = [
        {
            "id": b.get("id"),
            "title": b.get("title"),
            "description": b.get("description"),
            "excerpt": b.get("excerpt"),
            "pageCount": b.get("pageCount"),
            "publishDate": b.get("publishDate"),
        }
        for b in popular_books
    ]
    return {
        "totalBooks": total_books,
        "totalPageCount": total_page_count,
        "publicationDateRange": {"earliest": earliest, "latest": latest},
        "popularTitles": popular_titles,
    }

async def send_email_report(report: Dict[str, Any]) -> None:
    # TODO: Replace with real email sending functionality
    try:
        logger.info(f"Sending report email to {ANALYTICS_TEAM_EMAIL} with summary: "
                    f"Total Books: {report['totalBooks']}, Total Pages: {report['totalPageCount']}, "
                    f"Popular Titles: {len(report['popularTitles'])}")
        await asyncio.sleep(0.1)
    except Exception as e:
        logger.exception(f"Failed to send email report: {e}")

async def process_fetch_books(entity: Dict[str, Any]) -> None:
    books_data = await fetch_books()
    if books_data is None:
        entity['status'] = "failed"
        entity['error'] = "Failed to fetch books data"
        # Stop further processing by raising
        raise RuntimeError(entity['error'])
    entity['books_data'] = books_data

async def process_analyze_books(entity: Dict[str, Any]) -> None:
    books = entity.get('books_data', [])
    report_data = analyze_books(books)
    entity['report'] = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        **report_data,
    }

async def process_save_report(entity: Dict[str, Any]) -> None:
    # TODO: Replace with real persistence/store logic if needed
    # For prototype we store report inside entity itself
    entity['report_id'] = f"report-{datetime.now(timezone.utc).isoformat()}"
    # No external call needed, so just set id

async def process_send_email(entity: Dict[str, Any]) -> None:
    report = entity.get("report")
    if report:
        await send_email_report(report)

async def process_books_analysis_job(entity: Dict[str, Any]) -> None:
    entity['workflowProcessedAt'] = datetime.now(timezone.utc).isoformat()
    entity['status'] = "processing"
    try:
        await process_fetch_books(entity)
        await process_analyze_books(entity)
        await process_save_report(entity)
        await process_send_email(entity)
        entity['status'] = "completed"
    except Exception as e:
        entity['status'] = "failed"
        if 'error' not in entity:
            entity['error'] = str(e)
        logger.exception(f"Workflow for books_analysis_job failed: {e}")