#!/usr/bin/env python3
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

# Actual ingestion background task function (renamed from process_ingestion)
async def actual_ingestion(job_id: str, criteria: dict):
    try:
        logger.info(f"Starting ingestion job {job_id} with criteria: {criteria}")
        async with httpx.AsyncClient() as client:
            response = await client.get(PRODUCTS_API_URL)
            response.raise_for_status()
            data = response.json()
            update_data = {
                "data": data,
                "ingested_at": datetime.utcnow().isoformat(),
                "status": "finished"
            }
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="ingestion",
            entity_version=ENTITY_VERSION,
            technical_id=job_id,
            entity=update_data,
            meta={}
        )
        logger.info(f"Ingestion job {job_id} finished successfully.")
    except Exception as e:
        logger.exception(e)
        update_data = {
            "error": str(e),
            "ingested_at": datetime.utcnow().isoformat(),
            "status": "error"
        }
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="ingestion",
            entity_version=ENTITY_VERSION,
            technical_id=job_id,
            entity=update_data,
            meta={}
        )

# Workflow function for ingestion, applied before persistence.
async def process_ingestion(entity_data: dict):
    # Example workflow: mark the entity as processed and trigger background ingestion.
    entity_data["workflow_processed"] = True
    job_id = entity_data.get("job_id")
    criteria = entity_data.get("criteria")
    if job_id and criteria:
        asyncio.create_task(actual_ingestion(job_id, criteria))
    return entity_data

# Workflow function for aggregation, applied before persistence.
async def process_aggregation(entity_data: dict):
    # Example workflow: mark the aggregation entity as processed.
    entity_data["workflow_processed"] = True
    return entity_data

# Workflow function for report generation, applied before persistence.
async def process_report(entity_data: dict):
    # Example workflow: mark the report entity as processed.
    entity_data["workflow_processed"] = True
    return entity_data

@app.route("/api/ingest_data", methods=["POST"])
@validate_request(IngestDataRequest)
async def ingest_data(data: IngestDataRequest):
    try:
        criteria = {"date": data.date}
        job_id = str(uuid.uuid4())
        requested_at = datetime.utcnow().isoformat()
        job_obj = {
            "job_id": job_id,
            "status": "processing",
            "requested_at": requested_at,
            "criteria": criteria
        }
        # Pass the workflow function for ingestion
        id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="ingestion",
            entity_version=ENTITY_VERSION,
            entity=job_obj,
            workflow=process_ingestion
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
        aggregation_criteria = {"field": data.field, "operation": data.operation}
        dummy_result = {
            "field": aggregation_criteria.get("field", "unknown"),
            "operation": aggregation_criteria.get("operation", "unknown"),
            "result": 5000
        }
        agg_id = str(uuid.uuid4())
        agg_obj = {
            "aggregation_id": agg_id,
            "aggregated_data": dummy_result,
            "aggregated_at": datetime.utcnow().isoformat(),
            "criteria": aggregation_criteria
        }
        # Pass the workflow function for aggregation
        id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="aggregation",
            entity_version=ENTITY_VERSION,
            entity=agg_obj,
            workflow=process_aggregation
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
        date_range = {"start": data.start, "end": data.end}
        report_id = str(uuid.uuid4())
        dummy_report_url = f"http://localhost:8000/reports/{report_id}.pdf"
        report_obj = {
            "report_id": report_id,
            "report_type": data.report_type,
            "date_range": date_range,
            "report_url": dummy_report_url,
            "generated_at": datetime.utcnow().isoformat()
        }
        # Pass the workflow function for report generation
        id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="report",
            entity_version=ENTITY_VERSION,
            entity=report_obj,
            workflow=process_report
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
        reports = await entity_service.get_items(
            token=cyoda_token,
            entity_model="report",
            entity_version=ENTITY_VERSION
        )
        if not reports:
            return jsonify({"status": "error", "message": "No reports available"}), 404
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