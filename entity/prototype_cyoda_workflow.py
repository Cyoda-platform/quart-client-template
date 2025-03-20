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

# -------------------------------------------------------------------
# Workflow functions: these functions are applied to the entity
# asynchronously before persisting. They may change entity state
# and can trigger any async tasks (fire and forget) on other entity models.
# IMPORTANT: They must not call entity_service.add/update/delete on the
# current entity.
# -------------------------------------------------------------------

# Helper async function: actual ingestion process that fetches data
# and then updates a different entity_model ("ingestion") asynchronously.
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
        # Update the ingestion job status on a different entity model.
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

# Workflow function for ingestion.
async def process_ingestion(entity: dict):
    # Mark the ingestion entity as processed.
    entity["workflow_processed"] = True
    # Retrieve necessary values from the entity to launch the actual ingestion.
    job_id = entity.get("job_id")
    criteria = entity.get("criteria")
    if job_id and criteria:
        # Launch asynchronous ingestion task as a fire-and-forget function.
        asyncio.create_task(actual_ingestion(job_id, criteria))
    # Return the modified entity state for persistence.
    return entity

# Workflow function for aggregation.
async def process_aggregation(entity: dict):
    # Mark aggregation entity as processed.
    entity["workflow_processed"] = True
    # Example: if additional async tasks are needed, they can be launched here.
    # For instance, send notifications or compute additional metrics on a different entity model.
    return entity

# Workflow function for report generation.
async def process_report(entity: dict):
    # Mark the report entity as processed.
    entity["workflow_processed"] = True
    # Example: if additional processing is needed (e.g. fire asynchronous report creation tasks),
    # they can be launched here without affecting the current entity.
    return entity

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