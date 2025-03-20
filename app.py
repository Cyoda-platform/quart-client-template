from common.grpc_client.grpc_client import grpc_stream
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request
from dataclasses import dataclass

from common.config.config import ENTITY_VERSION
from app_init.app_init import entity_service, cyoda_token
from common.repository.cyoda.cyoda_init import init_cyoda

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

# Data classes for request validation
@dataclass
class IngestDataRequest:
    date: str

@dataclass
class AggregateDataRequest:
    field: str
    operation: str

@dataclass
class GenerateReportRequest:
    report_type: str
    start: str
    end: str

PRODUCTS_API_URL = "https://www.automationexercise.com/api/products"

# -------------------------------------------------------------------
# Endpoints: Minimal logic here. All additional asynchronous tasks and logic
# are moved to the corresponding workflow functions which are executed before persistence.
# -------------------------------------------------------------------

@app.route("/api/ingest_data", methods=["POST"])
@validate_request(IngestDataRequest)
async def ingest_data(data: IngestDataRequest):
    try:
        # Build the ingestion job criteria.
        criteria = {"date": data.date}
        job_id = str(uuid.uuid4())
        requested_at = datetime.utcnow().isoformat()
        # Prepare job object.
        job_obj = {
            "job_id": job_id,
            "status": "processing",
            "requested_at": requested_at,
            "criteria": criteria
        }
        # Pass the workflow function process_ingestion.
        id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="ingestion",
            entity_version=ENTITY_VERSION,
            entity=job_obj,
            )
        return jsonify({
            "status": "success",
            "message": "Data ingestion initiated",
            "data": {
                "job_id": id,
                "requested_at": requested_at
            }
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/aggregate_data", methods=["POST"])
@validate_request(AggregateDataRequest)
async def aggregate_data(data: AggregateDataRequest):
    try:
        # Build aggregation criteria.
        aggregation_criteria = {"field": data.field, "operation": data.operation}
        # Prepare dummy aggregated result.
        dummy_result = {
            "field": aggregation_criteria.get("field", "unknown"),
            "operation": aggregation_criteria.get("operation", "unknown"),
            "result": 5000
        }
        agg_id = str(uuid.uuid4())
        # Build aggregation job object.
        agg_obj = {
            "aggregation_id": agg_id,
            "aggregated_data": dummy_result,
            "aggregated_at": datetime.utcnow().isoformat(),
            "criteria": aggregation_criteria
        }
        # Pass the workflow function process_aggregation.
        id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="aggregation",
            entity_version=ENTITY_VERSION,
            entity=agg_obj,
            )
        return jsonify({
            "status": "success",
            "message": "Aggregation initiated",
            "aggregation_id": id
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/generate_report", methods=["POST"])
@validate_request(GenerateReportRequest)
async def generate_report(data: GenerateReportRequest):
    try:
        # Build date range for the report.
        date_range = {"start": data.start, "end": data.end}
        report_id = str(uuid.uuid4())
        dummy_report_url = f"http://localhost:8000/reports/{report_id}.pdf"
        # Build report object.
        report_obj = {
            "report_id": report_id,
            "report_type": data.report_type,
            "date_range": date_range,
            "report_url": dummy_report_url,
            "generated_at": datetime.utcnow().isoformat()
        }
        # Pass the workflow function process_report.
        id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="report",
            entity_version=ENTITY_VERSION,
            entity=report_obj,
            )
        return jsonify({
            "status": "success",
            "message": "Report generation initiated",
            "report_id": id
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/retrieve_report", methods=["GET"])
async def retrieve_report():
    try:
        # Retrieve all report items.
        reports = await entity_service.get_items(
            token=cyoda_token,
            entity_model="report",
            entity_version=ENTITY_VERSION
        )
        if not reports:
            return jsonify({"status": "error", "message": "No reports available"}), 404
        # Find the latest report based on the generated_at timestamp.
        latest_report = max(reports, key=lambda r: r.get("generated_at", ""))
        return jsonify({
            "status": "success",
            "report": {
                "report_id": latest_report.get("report_id"),
                "report_url": latest_report.get("report_url"),
                "generated_at": latest_report.get("generated_at")
            }
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)