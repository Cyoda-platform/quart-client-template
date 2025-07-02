from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

import httpx
import pandas as pd
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

import json
from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

@dataclass
class ProcessDataRequest:
    csv_url: str
    subscribers: list[str]
    analysis_type: str

async def download_csv(url: str) -> pd.DataFrame:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        # Use StringIO to read CSV from string content
        from io import StringIO
        df = pd.read_csv(StringIO(response.text))
        return df

def analyze_data(df: pd.DataFrame, analysis_type: str) -> Dict[str, Any]:
    # Defensive: if df empty, return empty summary
    if df.empty:
        return {
            "rows_processed": 0,
            "columns": [],
            "statistics": {},
            "note": "Empty dataset",
        }
    if analysis_type == "summary":
        desc = df.describe(include='all').to_dict()
        result = {
            "rows_processed": len(df),
            "columns": df.columns.tolist(),
            "statistics": desc,
        }
    else:
        desc = df.describe(include='all').to_dict()
        result = {
            "rows_processed": len(df),
            "columns": df.columns.tolist(),
            "statistics": desc,
            "note": f"Analysis type '{analysis_type}' not implemented, returning summary.",
        }
    return result

async def send_email_report(subscribers: list[str], report: Dict[str, Any]) -> None:
    # TODO: Replace with real email sending logic (SMTP / email API)
    if not subscribers:
        logger.warning("No subscribers specified for email report")
        return
    try:
        logger.info(f"Sending report email to subscribers: {subscribers}")
        logger.info(f"Report summary: Rows processed: {report.get('rows_processed')}, Columns: {report.get('columns')}")
        await asyncio.sleep(1)  # simulate sending email delay
    except Exception as e:
        logger.error(f"Failed to send email report: {e}")

@app.route("/api/process-data", methods=["POST"])
@validate_request(ProcessDataRequest)
async def process_data(data: ProcessDataRequest):
    job_id = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")

    # Initial entity with status processing and input data
    entity = {
        "job_id": job_id,
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat() + "Z",
        "csv_url": data.csv_url,
        "subscribers": data.subscribers,
        "analysis_type": data.analysis_type,
    }

    try:
        # Pass workflow function which will run all async logic before persistence
        technical_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            entity=entity
        )
    except Exception as e:
        logger.exception("Failed to add entity_job to entity_service")
        return jsonify({"status": "error", "message": "Could not initiate processing"}), 500

    return jsonify({
        "status": "processing_started",
        "message": "Data processing and email sending initiated.",
        "job_id": job_id,
    }), 202

@app.route("/api/results", methods=["GET"])
async def get_results():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.exception("Failed to get items from entity_service")
        return jsonify({"status": "error", "message": "Failed to get results"}), 500

    if not items:
        return jsonify({"status": "no_jobs", "message": "No processing jobs found."})

    latest_job = None
    latest_requested_at = ""
    for item in items:
        req_at = item.get("requestedAt", "")
        if req_at > latest_requested_at:
            latest_requested_at = req_at
            latest_job = item

    if not latest_job:
        return jsonify({"status": "no_jobs", "message": "No processing jobs found."})

    response = {
        "job_id": latest_job.get("job_id"),
        "status": latest_job.get("status"),
        "last_processed_at": latest_job.get("last_processed_at"),
        "summary": latest_job.get("result"),
        "error": latest_job.get("error"),
    }
    return jsonify(response)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
