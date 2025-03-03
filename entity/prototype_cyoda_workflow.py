#!/usr/bin/env python3
import asyncio
from datetime import datetime
from dataclasses import dataclass

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service
from common.config.config import ENTITY_VERSION

app = Quart(__name__)
QuartSchema(app)

# Use "job_report" as the entity_model name in all external service calls.
@dataclass
class JobRequest:
    recipient: str  # Use only primitive types

async def fetch_conversion_rate(symbol: str) -> float:
    # Use Binance API as external source
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        # TODO: Add error handling for non-200 responses or malformed data
        data = response.json()
        return float(data.get("price", 0.0))

async def send_email(recipient: str, report: dict):
    # TODO: Replace with actual email sending integration
    print(f"Sending email to {recipient} with report: {report}")
    await asyncio.sleep(0.1)  # Simulate email sending delay

# Workflow function for "job_report". It is applied to the job_report entity
# asynchronously before it is persisted.
async def process_job_report(entity: dict) -> dict:
    # entity already contains job details (e.g. "recipient", "requestedAt", "status")
    try:
        # Fetch conversion rates for BTC/USD and BTC/EUR
        btc_usd = await fetch_conversion_rate("BTCUSDT")
        btc_eur = await fetch_conversion_rate("BTCEUR")  # TODO: Verify if BTCEUR is supported by the API
    except Exception as e:
        entity["status"] = "error"
        entity["error"] = str(e)
        entity["timestamp"] = datetime.utcnow().isoformat() + "Z"
        return entity

    timestamp = datetime.utcnow().isoformat() + "Z"
    conversion_data = {
        "BTC_USD": btc_usd,
        "BTC_EUR": btc_eur
    }
    # Send email report; no further action on current entity is allowed
    await send_email(entity["recipient"], {
        "conversionRates": conversion_data,
        "timestamp": timestamp
    })

    # Modify the entity state directly; the updated state will be persisted
    entity["status"] = "success"
    entity["conversionRates"] = conversion_data
    entity["timestamp"] = timestamp
    entity["email_sent"] = True
    return entity

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# The controller now only creates the initial entity and passes it to the workflow.
@app.route("/job", methods=["POST"])
@validate_request(JobRequest)
async def create_job(data: JobRequest):
    recipient = data.recipient
    if not recipient:
        return jsonify({"error": "Recipient email is required"}), 400

    # Create the base entity, including all required initial details.
    job_report = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat() + "Z",
        "recipient": recipient
    }

    # Pass the workflow function; it will process the entity asynchronously before persistence.
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="job_report",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_report,  # the validated data object including initial job details
        workflow=process_job_report  # workflow function applied to the entity
    )
    return jsonify({"id": job_id}), 200

@app.route("/report/<job_id>", methods=["GET"])
async def get_report(job_id):
    report = await entity_service.get_item(
        token=cyoda_token,
        entity_model="job_report",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not report:
        return jsonify({"error": "Report not found"}), 404
    return jsonify(report), 200

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)