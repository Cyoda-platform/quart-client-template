#!/usr/bin/env python3
import asyncio
import uuid
from datetime import datetime

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)

# Define the external API configuration
EXTERNAL_API_URL = "https://services.cro.ie/cws/companies"
AUTHORIZATION_HEADER = "Basic dGVzdEBjcm8uaWU6ZGEwOTNhMDQtYzlkNy00NmQ3LTljODMtOWM5Zjg2MzBkNWUw"

# Data model for external API request validation
class ExternalDataRequest:
    company_name: str
    skip: int
    max: int

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

async def process_entity(job_id, params):
    """
    Process the external API request.
    This function uses aiohttp.ClientSession to call the external API and updates the job status via external entity service.
    """
    # Build URL with query parameters.
    query_params = {
        "company_name": params.get("company_name", ""),
        "skip": str(params.get("skip", 0)),
        "max": str(params.get("max", 5)),
        "htmlEnc": "1"
    }
    headers = {
        "accept": "application/json",
        "Authorization": AUTHORIZATION_HEADER
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(EXTERNAL_API_URL, params=query_params, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    update_data = {
                        "technical_id": job_id,
                        "status": "done",
                        "data": data,
                        "completedAt": datetime.utcnow().isoformat()
                    }
                else:
                    update_data = {
                        "technical_id": job_id,
                        "status": "error",
                        "error": f"External API returned status code {resp.status}"
                    }
    except Exception as e:
        update_data = {
            "technical_id": job_id,
            "status": "error",
            "error": str(e)
        }
    # Update the job record via external service.
    await entity_service.update_item(
        token=cyoda_token,
        entity_model="external_data",
        entity_version=ENTITY_VERSION,
        entity=update_data,
        meta={}
    )

@app.route("/external-data", methods=["POST"])
@validate_request(ExternalDataRequest)
async def external_data(data: ExternalDataRequest):
    """
    POST endpoint to retrieve external data.
    It creates a job record via the external entity service and fires off the processing task.
    """
    job = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "data": None
    }
    # Create a job record using the external service.
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="external_data",
        entity_version=ENTITY_VERSION,
        entity=job
    )
    # Fire and forget the external API processing task.
    asyncio.create_task(process_entity(job_id, data.__dict__))
    # Return the job ID so the client can later retrieve the results.
    return jsonify({"status": "processing", "job_id": job_id})

@app.route("/results", methods=["GET"])
async def get_results():
    """
    GET endpoint to retrieve stored job results from the external service.
    """
    results = await entity_service.get_items(
        token=cyoda_token,
        entity_model="external_data",
        entity_version=ENTITY_VERSION,
    )
    return jsonify({"status": "success", "results": results})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)