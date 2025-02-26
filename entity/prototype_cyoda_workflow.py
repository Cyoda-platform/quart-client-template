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

# Define workflow function to be applied to the entity before persistence.
# This function invokes any asynchronous tasks and updates the entity state.
async def process_companies_workflow(entity):
    # Add a timestamp for when the workflow was processed.
    entity["preProcessedAt"] = datetime.utcnow().isoformat()

    # Retrieve parameters stored from the incoming request.
    company_name = entity.get("companyName")
    skip = entity.get("skip", 0)
    max_records = entity.get("max", 5)

    # Build external API URL.
    url = (
        f"https://services.cro.ie/cws/companies?&company_name={company_name}"
        f"&skip={skip}&max={max_records}&htmlEnc=1"
    )
    headers = {
        "accept": "application/json",
        "Authorization": "Basic dGVzdEBjcm8uaWU6ZGEwOTNhMDQtYzlkNy00NmQ3LTljODMtOWM5Zjg2MzBkNWUw"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    # Update entity state to failed if external API did not return a 200 status.
                    entity["status"] = "failed"
                    entity["data"] = {"error": f"External API returned status {response.status}"}
                    return entity
                external_data = await response.json()
                # Update entity state to completed with the external data.
                entity["status"] = "completed"
                entity["data"] = external_data
    except Exception as e:
        # Mark the entity as failed when an exception occurs.
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
    await init_cyoda(cyoda_token)

@app.route("/companies", methods=["POST"])
@validate_request(CompanyRequest)  # Validation applied after route declaration.
async def create_company_job(data: CompanyRequest):
    # Use validated data from the request.
    company_name = data.company_name
    skip = data.skip
    max_records = data.max

    # Record initial job info and include original request parameters
    requested_at = datetime.utcnow().isoformat()
    job_data = {
        "status": "processing",
        "requestedAt": requested_at,
        "data": None,
        # Store extra parameters for use in the workflow function.
        "companyName": company_name,
        "skip": skip,
        "max": max_records
    }

    # Use external service to add job item.
    # The workflow function will be applied to the entity asynchronously before persistence.
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,  # always use this constant
        entity=job_data,  # the validated data object containing job info
        workflow=process_companies_workflow  # Workflow function applied to the entity
    )
    
    return jsonify({
        "job_id": job_id,
        "status": job_data["status"]
    }), 202

@app.route("/companies/<job_id>", methods=["GET"])
async def get_company_job(job_id):
    # Retrieve the job using external service call.
    job = await entity_service.get_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        technical_id=job_id
    )
    if not job:
        return jsonify({
            "error": "Job not found or processing failed",
            "status": "failed"
        }), 404
    return jsonify({
        "job_id": job_id,
        "status": job.get("status"),
        "data": job.get("data")
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)