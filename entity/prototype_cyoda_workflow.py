#!/usr/bin/env python3
import asyncio
from datetime import datetime

import aiohttp
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)

# External API configuration
EXTERNAL_API_URL = "https://services.cro.ie/cws/companies"
AUTHORIZATION_HEADER = "Basic dGVzdEBjcm8uaWU6ZGEwOTNhMDQtYzlkNy00NmQ3LTljODMtOWM5Zjg2MzBkNWUw"

# Data model for request validation
class ExternalDataRequest:
    company_name: str
    skip: int
    max: int

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

async def process_external_data(entity):
    # Workflow function that processes the external API call and updates the entity state.
    try:
        params = entity.get("params", {})
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
        async with aiohttp.ClientSession() as session:
            async with session.get(EXTERNAL_API_URL, params=query_params, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    entity["status"] = "done"
                    entity["data"] = data
                    entity["completedAt"] = datetime.utcnow().isoformat()
                else:
                    entity["status"] = "error"
                    entity["error"] = f"External API returned status code {resp.status}"
    except Exception as e:
        entity["status"] = "error"
        entity["error"] = str(e)
    finally:
        # Remove temporary parameters used only for processing
        entity.pop("params", None)
    return entity

@app.route("/external-data", methods=["POST"])
@validate_request(ExternalDataRequest)
async def external_data(data: ExternalDataRequest):
    # Create a job record with initial status and store external request parameters.
    job = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "data": None,
        "params": data.__dict__  # Save parameters for workflow processing.
    }
    # Persist the job record with the workflow function applied.
    # The workflow function will execute asynchronously before the entity is persisted.
    job_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="external_data",
        entity_version=ENTITY_VERSION,
        entity=job,
        workflow=process_external_data
    )
    return jsonify({"status": "processing", "job_id": job_id})

@app.route("/results", methods=["GET"])
async def get_results():
    # Retrieve job records from storage.
    try:
        results = await entity_service.get_items(
            token=cyoda_token,
            entity_model="external_data",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "success", "results": results})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)