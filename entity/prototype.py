```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

import httpx
import pandas as pd
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache to mock persistence: job_id -> job_data
entity_jobs: Dict[str, Dict[str, Any]] = {}

# Simple helper to generate job IDs (timestamp based)
def generate_job_id() -> str:
    return datetime.utcnow().strftime("%Y%m%d%H%M%S%f")

async def download_csv(url: str) -> pd.DataFrame:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        # Load CSV content into pandas DataFrame
        df = pd.read_csv(pd.compat.StringIO(response.text))
        return df

def analyze_data(df: pd.DataFrame, analysis_type: str) -> Dict[str, Any]:
    # TODO: Extend analysis types if needed
    if analysis_type == "summary":
        desc = df.describe(include='all').to_dict()
        result = {
            "rows_processed": len(df),
            "columns": df.columns.tolist(),
            "statistics": desc,
        }
    else:
        # Default fallback: basic summary
        desc = df.describe(include='all').to_dict()
        result = {
            "rows_processed": len(df),
            "columns": df.columns.tolist(),
            "statistics": desc,
            "note": f"Analysis type '{analysis_type}' not implemented, returning summary.",
        }
    return result

async def send_email_report(subscribers: list[str], report: Dict[str, Any]) -> None:
    # TODO: Replace this placeholder with real email sending logic (SMTP / email API)
    logger.info(f"Sending report email to subscribers: {subscribers}")
    logger.info(f"Report summary: Rows processed: {report.get('rows_processed')}, Columns: {report.get('columns')}")
    # Simulate sending delay
    await asyncio.sleep(1)

async def process_entity(job_id: str, csv_url: str, subscribers: list[str], analysis_type: str):
    try:
        logger.info(f"Job {job_id}: Starting data download from {csv_url}")
        df = await download_csv(csv_url)
        logger.info(f"Job {job_id}: Data downloaded, starting analysis")
        analysis_result = analyze_data(df, analysis_type)

        logger.info(f"Job {job_id}: Analysis complete, sending emails")
        await send_email_report(subscribers, analysis_result)

        entity_jobs[job_id].update({
            "status": "completed",
            "result": analysis_result,
            "last_processed_at": datetime.utcnow().isoformat() + "Z",
        })
        logger.info(f"Job {job_id}: Completed successfully")
    except Exception as e:
        entity_jobs[job_id].update({"status": "failed", "error": str(e)})
        logger.exception(f"Job {job_id}: Failed with exception")

@app.route("/api/process-data", methods=["POST"])
async def process_data():
    data = await request.get_json()
    csv_url = data.get("csv_url")
    subscribers = data.get("subscribers")
    analysis_type = data.get("analysis_type", "summary")

    if not csv_url or not subscribers or not isinstance(subscribers, list):
        return jsonify({"error": "Missing or invalid parameters: 'csv_url' and 'subscribers' are required."}), 400

    job_id = generate_job_id()
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat() + "Z",
    }

    # Fire and forget processing task
    asyncio.create_task(process_entity(job_id, csv_url, subscribers, analysis_type))

    return jsonify({
        "status": "processing_started",
        "message": "Data processing and email sending initiated.",
        "job_id": job_id,
    }), 202

@app.route("/api/results", methods=["GET"])
async def get_results():
    # Return the latest completed job result or status
    if not entity_jobs:
        return jsonify({"status": "no_jobs", "message": "No processing jobs found."})

    # Find last job by requestedAt descending
    latest_job_id, latest_job = max(entity_jobs.items(), key=lambda item: item[1].get("requestedAt", ""))
    response = {
        "job_id": latest_job_id,
        "status": latest_job.get("status"),
        "last_processed_at": latest_job.get("last_processed_at"),
        "summary": latest_job.get("result"),
        "error": latest_job.get("error"),
    }
    return jsonify(response)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
