from datetime import timezone, datetime
import logging
from quart import Blueprint, jsonify
from quart_schema import validate, validate_request

from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)
FINAL_STATES = {'FAILURE', 'SUCCESS', 'CANCELLED', 'CANCELLED_BY_USER', 'UNKNOWN', 'FINISHED'}
PROCESSING_STATE = 'PROCESSING'

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

FAKE_REST_API_BOOKS_URL = "https://fakerestapi.azurewebsites.net/api/v1/Books"
ANALYTICS_TEAM_EMAIL = "analytics-team@example.com"  # TODO: Replace with real email or config

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import asyncio
import httpx

@dataclass
class AnalyzeRequest:
    triggerDate: Optional[str] = None

async def fetch_books() -> Optional[Dict[str, Any]]:
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(FAKE_REST_API_BOOKS_URL)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.exception(f"Failed to fetch books from external API: {e}")
            return None

def analyze_books(books: List[Dict[str, Any]]) -> Dict[str, Any]:
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

@routes_bp.route("/api/books/analyze", methods=["POST"])
@validate_request(AnalyzeRequest)
async def analyze_books_endpoint(data: AnalyzeRequest):
    job_id = datetime.now(timezone.utc).isoformat()
    # Add the job entity with status queued and workflow function
    # Workflow function runs before persistence and performs all processing
    await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="books_analysis_job",
        entity_version="1",  # or ENTITY_VERSION if imported from config
        entity={
            "status": "queued",
            "requestedAt": job_id,
            "triggerDate": data.triggerDate
        }
    )
    return jsonify({
        "status": "success",
        "message": "Analysis job started",
        "jobId": job_id,
    })

@routes_bp.route("/api/books/report", methods=["GET"])
async def get_latest_report():
    try:
        reports = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="books_report",
            entity_version="1",  # or ENTITY_VERSION if imported from config
        )
        if not reports:
            return jsonify({"error": "No report available"}), 404
        latest_report = max(reports, key=lambda r: r.get("generatedAt", ""))
        return jsonify(latest_report)
    except Exception as e:
        logger.exception(f"Failed to get latest report: {e}")
        return jsonify({"error": "Failed to get latest report"}), 500