#!/usr/bin/env python3
from datetime import datetime
import asyncio
import aiohttp

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request  # For GET requests with query parameters, use validate_querystring if needed

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)  # Initialize schema support

# Workflow function applied to the entity asynchronously before persistence.
# This function is used to perform any asynchronous actions (external API calls, etc.)
# and update the entity state accordingly. It receives the entity data as the only argument.
async def process_companies_workflow(entity):
    try:
        # Add timestamp for workflow processing.
        entity["preProcessedAt"] = datetime.utcnow().isoformat()

        # Retrieve parameters stored in the entity.
        # These parameters were added during the request handling.
        company_name = entity.get("companyName")
        skip = entity.get("skip", 0)
        max_records = entity.get("max", 5)

        # Validate that mandatory parameter is present.
        if not company_name:
            # Update entity state to failed if company name is missing.
            entity["status"] = "failed"
            entity["data"] = {"error": "Missing company name parameter."}
            return entity

        # Build external API URL.
        url = (
            f"https://services.cro.ie/cws/companies?&company_name={company_name}"
            f"&skip={skip}&max={max_records}&htmlEnc=1"
        )
        headers = {
            "accept": "application/json",
            "Authorization": "Basic dGVzdEBjcm8uaWU6ZGEwOTNhMDQtYzlkNy00NmQ3LTljODMtOWM5Zjg2MzBkNWUw"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                # Check if external API call was successful.
                if response.status != 200:
                    # External API call failed; update entity state accordingly.
                    entity["status"] = "failed"
                    entity["data"] = {"error": f"External API returned status {response.status}"}
                    return entity

                # Process external API json response.
                external_data = await response.json()
                # Update entity state to completed along with the payload.
                entity["status"] = "completed"
                entity["data"] = external_data

    except Exception as e:
        # Capture any exceptions, update entity as failed, and attach error message.
        entity["status"] = "failed"
        entity["data"] = {"error": str(e)}
    return entity

# Define dataclass for POST request validation.
from dataclasses import dataclass

@dataclass
class CompanyRequest:
    company_name: str
    skip: int = 0
    max: int = 5

@app.before_serving
async def startup():
    # Initialize external system (e.g. cyoda)
    await init_cyoda(cyoda_token)

@app.route("/companies", methods=["POST"])
@validate_request(CompanyRequest)  # Validation is applied after route declaration.
async def create_company_job(data: CompanyRequest):
    # Extract validated request data.
    company_name = data.company_name
    skip = data.skip
    max_records = data.max

    # Record initial job info and store additional parameters required by the workflow.
    requested_at = datetime.utcnow().isoformat()
    job_data = {
        "status": "processing",          # initial status
        "requestedAt": requested_at,       # when the job was requested
        "data": None,                     # placeholder for data that will be updated by workflow
        # Store additional parameters required for the workflow.
        "companyName": company_name,
        "skip": skip,
        "max": max_records
    }

    # Use external service to add job item.
    # The workflow function is applied to the entity asynchronously before it is persisted.
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,    # Always use this constant
        entity=job_data,                  # the initial job data containing status and parameters
        workflow=process_companies_workflow  # Workflow function performing asynchronous tasks
    )

    # Return immediate response containing job identifier and current status.
    return jsonify({
        "job_id": job_id,
        "status": job_data.get("status", "processing")
    }), 202

@app.route("/companies/<job_id>", methods=["GET"])
async def get_company_job(job_id):
    # Retrieve the job item using external service call.
    job = await entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    # If job not found, return error.
    if not job:
        return jsonify({
            "error": "Job not found or processing failed",
            "status": "failed"
        }), 404

    # Return job details.
    return jsonify({
        "job_id": job_id,
        "status": job.get("status"),
        "data": job.get("data")
    })

if __name__ == '__main__':
    # Run the Quart application with specified settings.
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)