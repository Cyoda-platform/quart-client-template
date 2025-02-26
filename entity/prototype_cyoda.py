from datetime import datetime
import asyncio
import uuid

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request  # For GET requests with query parameters, use validate_querystring if needed

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)  # Initialize schema support

# Define dataclass for POST request validation
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
    # Use validated data from the request
    company_name = data.company_name
    skip = data.skip
    max_records = data.max

    # Record initial job info
    requested_at = datetime.utcnow().isoformat()
    job_data = {
        "status": "processing",
        "requestedAt": requested_at,
        "data": None  # Will be updated after processing
    }

    # Use external service to add job item. The entity_model is "companies".
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="companies",
        entity_version=ENTITY_VERSION,
        entity=job_data
    )

    # Fire-and-forget background processing task.
    asyncio.create_task(process_entity(job_id, company_name, skip, max_records))
    
    return jsonify({
        "job_id": job_id,
        "status": "processing"
    }), 202

@app.route("/companies/<job_id>", methods=["GET"])
async def get_company_job(job_id):
    # Retrieve the job using external service call
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

async def process_entity(job_id, company_name, skip, max_records):
    # Build external API URL
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
                    update_data = {
                        "status": "failed",
                        "data": {"error": f"External API returned status {response.status}"}
                    }
                    await entity_service.update_item(
                        token=cyoda_token,
                        entity_model="companies",
                        entity_version=ENTITY_VERSION,
                        entity=update_data,
                        meta={"technical_id": job_id}
                    )
                    return

                external_data = await response.json()
                update_data = {
                    "status": "completed",
                    "data": external_data
                }
                await entity_service.update_item(
                    token=cyoda_token,
                    entity_model="companies",
                    entity_version=ENTITY_VERSION,
                    entity=update_data,
                    meta={"technical_id": job_id}
                )
    except Exception as e:
        update_data = {
            "status": "failed",
            "data": {"error": str(e)}
        }
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="companies",
            entity_version=ENTITY_VERSION,
            entity=update_data,
            meta={"technical_id": job_id}
        )

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)