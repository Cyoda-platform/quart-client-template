import asyncio
import uuid
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request, abort
from quart_schema import QuartSchema, validate_request  # using validate_request for POST endpoints

from dataclasses import dataclass

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Dummy schema for POST /job request
@dataclass
class JobRequest:
    dummy: str = ""  # TODO: This schema is a placeholder since no data is expected. Update if requirements change.

# Global in-memory cache to store reports
reports = {}

# TODO: Replace with proper email sending integration
async def send_email(report: dict):
    # Placeholder: Simulate sending email with an async sleep
    await asyncio.sleep(0.1)
    logger.info(f"Email sent with report: {report}")
    # TODO: Integrate actual email service (e.g., SMTP, SendGrid, etc.)

async def fetch_conversion_rates() -> dict:
    url_btc_usd = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    url_btc_eur = "https://api.binance.com/api/v3/ticker/price?symbol=BTCEUR"
    try:
        async with httpx.AsyncClient() as client:
            resp_usd, resp_eur = await asyncio.gather(
                client.get(url_btc_usd),
                client.get(url_btc_eur)
            )
        data_usd = resp_usd.json()
        data_eur = resp_eur.json()
        # Expecting API response to have a 'price' key
        return {
            "btc_usd": float(data_usd.get("price", 0)),
            "btc_eur": float(data_eur.get("price", 0))
        }
    except Exception as e:
        logger.exception(e)
        # Return default/fallback rates or raise error as needed
        raise

async def process_entity(job_id: str):
    try:
        # Update the report status to processing
        reports[job_id]["status"] = "processing"
        # Fetch conversion rates from external API
        rates = await fetch_conversion_rates()
        timestamp = datetime.utcnow().isoformat()
        
        # Build the report object
        report = {
            "report_id": job_id,
            "btc_usd": rates["btc_usd"],
            "btc_eur": rates["btc_eur"],
            "timestamp": timestamp,
            "status": "completed"
        }
        
        # Save the report in the global in-memory cache
        reports[job_id] = report
        
        # Trigger email sending (fire and forget)
        asyncio.create_task(send_email(report))
        return report

    except Exception as e:
        logger.exception(e)
        # Update report status to failed
        reports[job_id]["status"] = "failed"
        # In a real implementation, handle retries or error reporting.
        raise

# For POST endpoints, route decorator comes first, then validate_request (workaround for a quart-schema issue)
@app.route("/job", methods=["POST"])
@validate_request(JobRequest)
async def create_job(data: JobRequest):
    # Create a new job with unique id and record request time
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()
    reports[job_id] = {"status": "received", "requestedAt": requested_at}

    # Fire and forget the processing task.
    try:
        # Await the processing for the prototype user feedback.
        report = await asyncio.create_task(process_entity(job_id))
    except Exception:
        abort(500, description="An error occurred while processing the job.")
    
    response = {
        "report_id": report["report_id"],
        "btc_usd": report["btc_usd"],
        "btc_eur": report["btc_eur"],
        "timestamp": report["timestamp"],
        "message": "Report successfully generated and email sent"
    }
    return jsonify(response)

# GET endpoint does not require validation as it only retrieves a stored report using a URL parameter
@app.route("/report/<string:job_id>", methods=["GET"])
async def get_report(job_id: str):
    report = reports.get(job_id)
    if not report or report.get("status") != "completed":
        abort(404, description="Report not found or not completed yet.")
    
    response = {
        "report_id": report["report_id"],
        "btc_usd": report["btc_usd"],
        "btc_eur": report["btc_eur"],
        "timestamp": report["timestamp"]
    }
    return jsonify(response)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)