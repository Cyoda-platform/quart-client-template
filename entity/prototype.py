import asyncio
import uuid
from datetime import datetime
from dataclasses import dataclass

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request  # Note: For GET requests with query parameters, use validate_querystring as needed

app = Quart(__name__)
QuartSchema(app)  # Initialize schema support

# Define dataclass for POST request validation
@dataclass
class CompanyRequest:
    company_name: str
    skip: int = 0
    max: int = 5

# In-memory cache for job persistence. This is a simple placeholder.
entity_jobs = {}


@app.route("/companies", methods=["POST"])
@validate_request(CompanyRequest)  # Workaround: For POST request, validation is applied after route declaration.
async def create_company_job(data: CompanyRequest):
    # Use validated data from the request
    company_name = data.company_name
    skip = data.skip
    max_records = data.max

    # Generate a unique job id and record initial job info
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": requested_at,
        "data": None  # Will be updated after processing
    }

    # Fire-and-forget background processing task.
    asyncio.create_task(process_entity(job_id, company_name, skip, max_records))

    return jsonify({
        "job_id": job_id,
        "status": "processing"
    }), 202


@app.route("/companies/<job_id>", methods=["GET"])
async def get_company_job(job_id):
    # No validation decorator for route parameters in GET requests per requirements.
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({
            "error": "Job not found or processing failed",
            "status": "failed"
        }), 404
    return jsonify({
        "job_id": job_id,
        "status": job["status"],
        "data": job["data"]
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
                    # TODO: implement more comprehensive error handling/logging
                    entity_jobs[job_id]["status"] = "failed"
                    entity_jobs[job_id]["data"] = {"error": f"External API returned status {response.status}"}
                    return

                # Retrieve and process JSON data. This can be extended to perform additional calculations.
                external_data = await response.json()

                # Update the in-memory datastore with processed data
                entity_jobs[job_id]["status"] = "completed"
                entity_jobs[job_id]["data"] = external_data

    except Exception as e:
        # TODO: Enhance exception tracking, possibly with a logging service.
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["data"] = {"error": str(e)}


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)