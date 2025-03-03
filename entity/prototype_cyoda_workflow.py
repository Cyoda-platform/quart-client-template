#!/usr/bin/env python3
import asyncio
import uuid
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request, abort
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
        logger.exception(e)
        raise

# Workflow function applied to report entity before persistence.
# It MUST be named with the prefix 'process_' followed by the entity name.
async def process_report(entity: dict) -> dict:
    logger.info("Applying workflow modifications to report entity")
    # Example: add a flag indicating workflow has been applied.
    entity["workflow_applied"] = True
    return entity

# Process the job: update status, fetch rates, save completed report and trigger email.
async def process_entity(job_id: str):
    try:
        # Update job status to "processing"
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="report",
            entity_version=ENTITY_VERSION,
            entity={"status": "processing"},
            technical_id=job_id,
            meta={}
        )
        # Fetch conversion rates.
        rates = await fetch_conversion_rates()
        timestamp = datetime.utcnow().isoformat()
        report = {
            "report_id": job_id,
            "btc_usd": rates["btc_usd"],
            "btc_eur": rates["btc_eur"],
            "timestamp": timestamp,
            "status": "completed"
        }
        # Update job record with completed report.
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="report",
            entity_version=ENTITY_VERSION,
            entity=report,
            technical_id=job_id,
            meta={}
        )
        # Fire off email asynchronously.
        asyncio.create_task(send_email(report))
        return report
    except Exception as e:
        logger.exception(e)
        # Mark job as failed if error occurs.
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="report",
            entity_version=ENTITY_VERSION,
            entity={"status": "failed"},
            technical_id=job_id,
            meta={}
        )
        raise

# POST endpoint: Create a new job record and trigger async processing.
@app.route("/job", methods=["POST"])
@validate_request(JobRequest)
async def create_job(data: JobRequest):
    requested_at = datetime.utcnow().isoformat()
    # Build initial job record with status "received"
    job_data = {"status": "received", "requestedAt": requested_at}
    try:
        # Add new job via external entity_service.
        # Note: workflow function 'process_report' is applied to the entity before persistence.
        job_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="report",
            entity_version=ENTITY_VERSION,
            entity=job_data,
            workflow=process_report
        )
    except Exception as e:
        logger.exception(e)
        abort(500, description="Could not create job record.")

    # Fire and forget the background processing task.
    asyncio.create_task(process_entity(job_id))

    # Return the generated job id; report details will be available later via the GET endpoint.
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
        logger.exception(e)
        abort(500, description="Error retrieving report.")

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