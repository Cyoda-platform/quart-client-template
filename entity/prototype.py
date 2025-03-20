import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Data classes for request validation
@dataclass
class IngestDataRequest:
    # For simplicity, the request is flattened.
    # TODO: Adjust if nested structure {"criteria": {"date": "YYYY-MM-DD"}} is needed.
    date: str

@dataclass
class AggregateDataRequest:
    field: str
    operation: str

@dataclass
class GenerateReportRequest:
    report_type: str
    # For simplicity, the date_range is flattened.
    # TODO: Adjust if nested structure {"date_range": {"start": "...", "end": "..."}} is needed.
    start: str
    end: str

# Global caches for our prototype
ingestion_store = {}  # Stores ingested product data keyed by ingestion id
aggregation_store = {}  # Stores results of aggregation keyed by aggregation id
report_store = {}  # Stores generated reports keyed by report id

# External API endpoint for product data (using real API)
PRODUCTS_API_URL = "https://www.automationexercise.com/api/products"

# Utility function to simulate asynchronous processing
async def process_ingestion(job_id: str, criteria: dict):
    try:
        logger.info(f"Starting ingestion job {job_id} with criteria: {criteria}")
        async with httpx.AsyncClient() as client:
            # TODO: adapt request parameters based on criteria if needed
            response = await client.get(PRODUCTS_API_URL)
            response.raise_for_status()
            data = response.json()
            # Save the ingested data to the local cache
            ingestion_store[job_id] = {
                "data": data,
                "ingested_at": datetime.utcnow().isoformat()
            }
            logger.info(f"Ingestion job {job_id} finished successfully.")
    except Exception as e:
        logger.exception(e)
        ingestion_store[job_id] = {
            "error": str(e),
            "ingested_at": datetime.utcnow().isoformat()
        }

@app.route("/api/ingest_data", methods=["POST"])
@validate_request(IngestDataRequest)  # Workaround: for POST, route comes first then validation decorator
async def ingest_data(data: IngestDataRequest):
    try:
        # Use the validated request data
        criteria = {"date": data.date}
        job_id = str(uuid.uuid4())
        requested_at = datetime.utcnow().isoformat()

        # Track the ingestion job in a local cache (fire and forget processing task)
        ingestion_store[job_id] = {"status": "processing", "requestedAt": requested_at}
        asyncio.create_task(process_ingestion(job_id, criteria))

        return jsonify({
            "status": "success",
            "message": "Data ingestion initiated",
            "data": {
                "job_id": job_id,
                "requested_at": requested_at
            }
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/aggregate_data", methods=["POST"])
@validate_request(AggregateDataRequest)  # Workaround: route first then validation decorator for POST endpoints
async def aggregate_data(data: AggregateDataRequest):
    try:
        aggregation_criteria = {"field": data.field, "operation": data.operation}
        # TODO: Implement actual aggregation logic based on the criteria and ingested data.
        # For now, we simulate aggregation using a dummy value.
        dummy_result = {
            "field": aggregation_criteria.get("field", "unknown"),
            "operation": aggregation_criteria.get("operation", "unknown"),
            "result": 5000  # Dummy aggregated value
        }
        agg_id = str(uuid.uuid4())
        aggregation_store[agg_id] = {
            "aggregated_data": dummy_result,
            "aggregated_at": datetime.utcnow().isoformat()
        }
        return jsonify({
            "status": "success",
            "aggregated_data": dummy_result,
            "aggregation_id": agg_id
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/generate_report", methods=["POST"])
@validate_request(GenerateReportRequest)  # Workaround: route first then validation decorator for POST endpoints
async def generate_report(data: GenerateReportRequest):
    try:
        date_range = {"start": data.start, "end": data.end}
        report_type = data.report_type
        # TODO: Use actual aggregated data and generate a report.
        # For now, we simulate report generation with a dummy URL.
        report_id = str(uuid.uuid4())
        dummy_report_url = f"http://localhost:8000/reports/{report_id}.pdf"
        report_store[report_id] = {
            "report_type": report_type,
            "date_range": date_range,
            "report_url": dummy_report_url,
            "generated_at": datetime.utcnow().isoformat()
        }
        # TODO: Implement sending email to admin once report is generated.
        return jsonify({
            "status": "success",
            "report_url": dummy_report_url,
            "report_id": report_id
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/retrieve_report", methods=["GET"])
async def retrieve_report():
    try:
        # For prototype, we simply return the latest report if available.
        if not report_store:
            return jsonify({
                "status": "error",
                "message": "No reports available"
            }), 404
        # Retrieve the most recent report (naively)
        latest_report_id = sorted(report_store.keys())[-1]
        report = report_store[latest_report_id]
        return jsonify({
            "status": "success",
            "report": {
                "report_id": latest_report_id,
                "report_url": report["report_url"],
                "generated_at": report["generated_at"]
            }
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)