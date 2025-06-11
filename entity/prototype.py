```python
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache to hold the last generated report and job statuses
# Structure: {"report": {...}, "jobs": {job_id: {...}}}
app.state.cache: Dict[str, Any] = {"report": None, "jobs": {}}

FAKE_REST_API_BOOKS_URL = "https://fakerestapi.azurewebsites.net/api/v1/Books"
ANALYTICS_TEAM_EMAIL = "analytics-team@example.com"  # TODO: Replace with real email or config


async def fetch_books() -> Optional[Dict[str, Any]]:
    """Fetch books data from the Fake REST API."""
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(FAKE_REST_API_BOOKS_URL)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.exception(f"Failed to fetch books from external API: {e}")
            return None


def analyze_books(books: list) -> Dict[str, Any]:
    """
    Analyze books data:
    - totalBooks
    - totalPageCount
    - publicationDateRange (earliest, latest)
    - popularTitles (top 5 by pageCount)
    """
    if not books:
        return {
            "totalBooks": 0,
            "totalPageCount": 0,
            "publicationDateRange": {"earliest": None, "latest": None},
            "popularTitles": [],
        }

    total_books = len(books)
    total_page_count = sum(book.get("pageCount", 0) for book in books)

    # Parse publishDate strings to date objects for range calculation.
    # Dates are assumed to be ISO 8601 strings.
    dates = []
    for book in books:
        pd = book.get("publishDate")
        if pd:
            try:
                # Some dates might be date-only, some with time, normalize to date string
                dt = datetime.fromisoformat(pd.rstrip("Z"))
                dates.append(dt.date())
            except Exception:
                # Ignore invalid date formats
                pass
    if dates:
        earliest = min(dates).isoformat()
        latest = max(dates).isoformat()
    else:
        earliest = None
        latest = None

    # Popular titles: top 5 books by pageCount descending
    popular_books = sorted(books, key=lambda b: b.get("pageCount", 0), reverse=True)[:5]

    popular_titles = []
    for b in popular_books:
        popular_titles.append(
            {
                "id": b.get("id"),
                "title": b.get("title"),
                "description": b.get("description"),
                "excerpt": b.get("excerpt"),
                "pageCount": b.get("pageCount"),
                "publishDate": b.get("publishDate"),
            }
        )

    return {
        "totalBooks": total_books,
        "totalPageCount": total_page_count,
        "publicationDateRange": {"earliest": earliest, "latest": latest},
        "popularTitles": popular_titles,
    }


async def send_email_report(report: Dict[str, Any]) -> None:
    """
    Mock sending email report to analytics team.
    TODO: Replace with real email sending functionality.
    """
    # For prototype, just log the report sending
    logger.info(f"Sending report email to {ANALYTICS_TEAM_EMAIL} with summary: "
                f"Total Books: {report['totalBooks']}, Total Pages: {report['totalPageCount']}, "
                f"Popular Titles: {len(report['popularTitles'])}")
    # Simulate async email sending delay
    await asyncio.sleep(0.1)


async def process_analysis_job(job_id: str, trigger_date: Optional[str]) -> None:
    """
    Background task to fetch, analyze, generate report and send email.
    Stores final report in app.state.cache and updates job status.
    """
    try:
        app.state.cache["jobs"][job_id]["status"] = "processing"
        logger.info(f"Job {job_id} started analysis process")

        books_data = await fetch_books()
        if books_data is None:
            app.state.cache["jobs"][job_id]["status"] = "failed"
            app.state.cache["jobs"][job_id]["error"] = "Failed to fetch books data"
            return

        report_data = analyze_books(books_data)

        # Add metadata
        report = {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            **report_data,
        }

        # Store report in cache (overwrite previous)
        app.state.cache["report"] = report

        # Send email (mock)
        await send_email_report(report)

        app.state.cache["jobs"][job_id]["status"] = "completed"
        logger.info(f"Job {job_id} completed successfully")

    except Exception as e:
        app.state.cache["jobs"][job_id]["status"] = "failed"
        app.state.cache["jobs"][job_id]["error"] = str(e)
        logger.exception(f"Job {job_id} failed with exception: {e}")


@app.route("/api/books/analyze", methods=["POST"])
async def analyze_books_endpoint():
    """
    POST endpoint to trigger analysis job.
    Request JSON optionally contains "triggerDate" (ISO date string).
    Returns job status and summary if available.
    """
    data = await request.get_json(silent=True) or {}
    trigger_date = data.get("triggerDate")

    job_id = datetime.now(timezone.utc).isoformat()
    app.state.cache["jobs"][job_id] = {
        "status": "queued",
        "requestedAt": job_id,
    }

    # Fire and forget background analysis task
    asyncio.create_task(process_analysis_job(job_id, trigger_date))

    # Return immediate response with job info
    return jsonify({
        "status": "success",
        "message": "Analysis job started",
        "jobId": job_id,
    })


@app.route("/api/books/report", methods=["GET"])
async def get_latest_report():
    """
    GET endpoint returns the last generated report or 404 if none exists.
    """
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
```
