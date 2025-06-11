import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Request schema for POST /api/books/analyze
@dataclass
class AnalyzeRequest:
    triggerDate: Optional[str] = None

# In-memory cache to hold the last generated report and job statuses
app.state.cache: Dict[str, Any] = {"report": None, "jobs": {}}

FAKE_REST_API_BOOKS_URL = "https://fakerestapi.azurewebsites.net/api/v1/Books"
ANALYTICS_TEAM_EMAIL = "analytics-team@example.com"  # TODO: Replace with real email or config

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
    logger.info(f"Sending report email to {ANALYTICS_TEAM_EMAIL} with summary: "
                f"Total Books: {report['totalBooks']}, Total Pages: {report['totalPageCount']}, "
                f"Popular Titles: {len(report['popularTitles'])}")
    await asyncio.sleep(0.1)

async def process_analysis_job(job_id: str, trigger_date: Optional[str]) -> None:
    try:
        app.state.cache["jobs"][job_id]["status"] = "processing"
        logger.info(f"Job {job_id} started analysis process")
        books_data = await fetch_books()
        if books_data is None:
            app.state.cache["jobs"][job_id]["status"] = "failed"
            app.state.cache["jobs"][job_id]["error"] = "Failed to fetch books data"
            return
        report_data = analyze_books(books_data)
        report = {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            **report_data,
        }
        app.state.cache["report"] = report
        await send_email_report(report)
        app.state.cache["jobs"][job_id]["status"] = "completed"
        logger.info(f"Job {job_id} completed successfully")
    except Exception as e:
        app.state.cache["jobs"][job_id]["status"] = "failed"
        app.state.cache["jobs"][job_id]["error"] = str(e)
        logger.exception(f"Job {job_id} failed with exception: {e}")

@app.route("/api/books/analyze", methods=["POST"])
@validate_request(AnalyzeRequest)  # workaround: validation last for POST due to quart-schema defect
async def analyze_books_endpoint(data: AnalyzeRequest):
    job_id = datetime.now(timezone.utc).isoformat()
    app.state.cache["jobs"][job_id] = {
        "status": "queued",
        "requestedAt": job_id,
    }
    asyncio.create_task(process_analysis_job(job_id, data.triggerDate))
    return jsonify({
        "status": "success",
        "message": "Analysis job started",
        "jobId": job_id,
    })

@app.route("/api/books/report", methods=["GET"])
async def get_latest_report():
    report = app.state.cache.get("report")
    if not report:
        return jsonify({"error": "No report available"}), 404
    return jsonify(report)

if __name__ == "__main__":
    import logging
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO,
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)