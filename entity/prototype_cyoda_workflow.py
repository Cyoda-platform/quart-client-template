#!/usr/bin/env python3
import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, abort
from quart_schema import QuartSchema, validate_request
from dataclasses import dataclass

# Import external service and config constants
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Startup: initialize cyoda before serving requests
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Dummy schema for POST /job request.
@dataclass
class JobRequest:
    dummy: str = ""  # Placeholder: update as needed

# Dummy email sending integration.
async def send_email(report: dict):
    # Simulate async email sending.
    await asyncio.sleep(0.1)
    logger.info(f"Email sent with report: {report}")

# Fetch conversion rates from external API.
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
        return {
            "btc_usd": float(data_usd.get("price", 0)),
            "btc_eur": float(data_eur.get("price", 0))
        }
    except Exception as e:
        logger.exception("Error fetching conversion rates")
        raise

# Workflow function applied to report entity before persistence.
# It MUST be named with the prefix 'process_' followed by the entity name.
async def process_report(entity: dict) -> dict:
    try:
        # Mark the entity as processing before doing any asynchronous tasks.
        entity["status"] = "processing"
        # Fetch conversion rates.
        rates = await fetch_conversion_rates()
        # Set timestamp for the report.
        timestamp = datetime.utcnow().isoformat()
        # Update the entity with complete report details.
        entity["btc_usd"] = rates["btc_usd"]
        entity["btc_eur"] = rates["btc_eur"]
        entity["timestamp"] = timestamp
        entity["status"] = "completed"
        # Optional flag to indicate workflow has been applied.
        entity["workflow_applied"] = True
        # Trigger asynchronous email sending (fire-and-forget).
        asyncio.create_task(send_email(entity))
    except Exception as e:
        logger.exception("Error during workflow processing for report")
        # On error, mark the entity as failed.
        entity["status"] = "failed"
    # Return the modified entity; this new state will be persisted.
    return entity

# POST endpoint: Create a new job record.
# The workflow function process_report is applied asynchronously to the entity
# before persistence, offloading the business logic from the controller.
@app.route("/job", methods=["POST"])
@validate_request(JobRequest)
async def create_job(data: JobRequest):
    # Build initial job record with status "received".
    requested_at = datetime.utcnow().isoformat()
    job_data = {"status": "received", "requestedAt": requested_at}
    try:
        # Add new job via external entity_service.
        # The workflow function (process_report) will update the entity
        # with conversion rates, timestamp, and trigger email sending.
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="report",
            entity_version=ENTITY_VERSION,
            entity=job_data,
            workflow=process_report
        )
    except Exception as e:
        logger.exception("Failed to create job record")
        abort(500, description="Could not create job record.")
    # Return the generated job id; full report details can be retrieved later.
    return jsonify({
        "report_id": job_id,
        "message": "Job created. Retrieve result later using the report endpoint."
    })

# GET endpoint: Retrieve the completed report using the job id.
@app.route("/report/<string:job_id>", methods=["GET"])
async def get_report(job_id: str):
    try:
        report = await entity_service.get_item(
            token=cyoda_token,
            entity_model="report",
            entity_version=ENTITY_VERSION,
            technical_id=job_id
        )
    except Exception as e:
        logger.exception("Error retrieving report")
        abort(500, description="Error retrieving report.")
    # Ensure report exists and is completed.
    if not report or report.get("status") != "completed":
        abort(404, description="Report not found or not completed yet.")
    return jsonify({
        "report_id": report.get("report_id"),
        "btc_usd": report.get("btc_usd"),
        "btc_eur": report.get("btc_eur"),
        "timestamp": report.get("timestamp")
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)