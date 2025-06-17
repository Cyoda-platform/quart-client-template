import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request
import httpx
import uuid

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

entity_name = "report"  # underscore lowercase

@dataclass
class AnalyzeBooksRequest:
    triggeredBy: str
    date: Optional[str] = None

def parse_iso_date(date_str: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(date_str.rstrip("Z")).replace(tzinfo=timezone.utc)
    except Exception:
        logger.exception(f"Failed to parse date: {date_str}")
        return None

async def fetch_books() -> Any:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get("https://fakerestapi.azurewebsites.net/api/v1/Books")
        resp.raise_for_status()
        return resp.json()

def analyze_books_data(books: list) -> Dict[str, Any]:
    total_page_count = 0
    publication_dates = []
    for book in books:
        page_count = book.get("pageCount", 0) or 0
        total_page_count += page_count
        publish_date_str = book.get("publishDate")
        publish_date = parse_iso_date(publish_date_str)
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

    return {
        "totalBooks": len(books),
        "totalPageCount": total_page_count,
        "publicationDateRange": {"earliest": earliest, "latest": latest},
        "popularTitles": popular_titles,
        "summary": summary,
    }

async def send_email_report(report: Dict[str, Any]) -> None:
    try:
        # Placeholder for real email sending logic
        logger.info(f"Sending email report to analytics@example.com:\n{report['summary']}")
        await asyncio.sleep(0.1)
    except Exception:
        logger.exception("Failed to send email report")

@app.route("/analyze-books", methods=["POST"])
@validate_request(AnalyzeBooksRequest)
async def analyze_books(data: AnalyzeBooksRequest):
    triggered_by = data.triggeredBy
    requested_at = data.date or datetime.now(timezone.utc).isoformat()
    job_id = str(uuid.uuid4())

    initial_entity = {
        "reportId": job_id,
        "status": "processing",
        "requestedAt": requested_at,
        "triggeredBy": triggered_by,
    }

    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=initial_entity
        )
    except Exception as e:
        logger.exception(f"Failed to add initial report status for job {job_id}: {e}")
        return jsonify({"status": "error", "message": "Failed to initiate analysis job."}), 500

    return jsonify({
        "status": "success",
        "message": "Book data analysis started.",
        "reportId": job_id,
    })

@app.route("/reports/<report_id>", methods=["GET"])
async def get_report(report_id):
    try:
        report = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            technical_id=report_id
        )
    except Exception as e:
        logger.exception(f"Failed to get report {report_id}: {e}")
        return jsonify({"error": "Report not found"}), 404

    if not report:
        return jsonify({"error": "Report not found"}), 404
    if report.get("status") == "processing":
        return jsonify({"status": "processing"}), 202
    if report.get("status") == "failed":
        return jsonify({"status": "failed", "error": report.get("error")}), 500
    return jsonify(report)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
