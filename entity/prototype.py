import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
import httpx
import uuid

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for reports: report_id -> report data
reports_cache: Dict[str, Dict[str, Any]] = {}

FAKE_REST_API_BOOKS_URL = "https://fakerestapi.azurewebsites.net/api/v1/Books"
ANALYTICS_TEAM_EMAIL = "analytics@example.com"  # TODO: Make configurable if needed

@dataclass
class AnalyzeBooksRequest:
    triggeredBy: str
    date: Optional[str] = None

# Helper: parse ISO date safely
def parse_iso_date(date_str: str) -> datetime:
    try:
        return datetime.fromisoformat(date_str.rstrip("Z")).replace(tzinfo=timezone.utc)
    except Exception:
        logger.exception(f"Failed to parse date: {date_str}")
        return None

async def fetch_books() -> Any:
    async with httpx.AsyncClient() as client:
        resp = await client.get(FAKE_REST_API_BOOKS_URL)
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
    # TODO: Implement real email sending logic here
    logger.info(f"Sending email report to {ANALYTICS_TEAM_EMAIL}:\n{report['summary']}")
    await asyncio.sleep(0.1)

async def process_analysis_job(job_id: str, triggered_by: str, requested_at: str) -> None:
    try:
        logger.info(f"Start processing analysis job {job_id} triggered by {triggered_by} at {requested_at}")
        books = await fetch_books()
        analysis = analyze_books_data(books)

        report_data = {
            "reportId": job_id,
            "generatedOn": datetime.now(timezone.utc).isoformat(),
            **analysis,
        }

        reports_cache[job_id] = report_data
        await send_email_report(report_data)
        logger.info(f"Analysis job {job_id} completed and report generated.")
    except Exception as e:
        logger.exception(f"Failed processing analysis job {job_id}: {e}")
        reports_cache[job_id] = {"status": "failed", "error": str(e)}

@app.route("/analyze-books", methods=["POST"])
# Workaround for quart-schema defect: validation must be last for POST
@validate_request(AnalyzeBooksRequest)
async def analyze_books(data: AnalyzeBooksRequest):
    triggered_by = data.triggeredBy
    requested_at = data.date or datetime.now(timezone.utc).isoformat()
    job_id = str(uuid.uuid4())
    reports_cache[job_id] = {"status": "processing", "requestedAt": requested_at}
    asyncio.create_task(process_analysis_job(job_id, triggered_by, requested_at))
    return jsonify({
        "status": "success",
        "message": "Book data analysis started.",
        "reportId": job_id,
    })

@app.route("/reports/<report_id>", methods=["GET"])
async def get_report(report_id):
    report = reports_cache.get(report_id)
    if not report:
        return jsonify({"error": "Report not found"}), 404
    if report.get("status") == "processing":
        return jsonify({"status": "processing"}), 202
    if report.get("status") == "failed":
        return jsonify({"status": "failed", "error": report.get("error")}), 500
    return jsonify(report)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)