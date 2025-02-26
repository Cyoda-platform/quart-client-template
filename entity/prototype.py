import asyncio
import uuid
from datetime import datetime

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema  # Only one line per instructions

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for job results.
entity_jobs = {}

# External API configuration
EXTERNAL_API_URL = "https://services.cro.ie/cws/companies"
AUTHORIZATION_HEADER = "Basic dGVzdEBjcm8uaWU6ZGEwOTNhMDQtYzlkNy00NmQ3LTljODMtOWM5Zjg2MzBkNWUw"


async def process_entity(job_id, params):
    """
    Process the external API request.
    This function uses aiohttp.ClientSession to call the external API and updates the job status.
    """
    # Build URL with query parameters.
    query_params = {
        "company_name": params.get("company_name", ""),
        "skip": params.get("skip", "0"),
        "max": params.get("max", "5"),
        "htmlEnc": "1"
    }

    headers = {
        "accept": "application/json",
        "Authorization": AUTHORIZATION_HEADER
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(EXTERNAL_API_URL, params=query_params, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Update job status to done with retrieved data.
                    entity_jobs[job_id]["status"] = "done"
                    entity_jobs[job_id]["data"] = data
                    entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
                else:
                    # TODO: Handle non-200 responses with more granular error info.
                    entity_jobs[job_id]["status"] = "error"
                    entity_jobs[job_id]["error"] = f"External API returned status code {resp.status}"
        except Exception as e:
            # TODO: Improve error handling and logging.
            entity_jobs[job_id]["status"] = "error"
            entity_jobs[job_id]["error"] = str(e)


@app.route("/external-data", methods=["POST"])
async def external_data():
    """
    POST endpoint to retrieve external data.
    It fires and forgets the task for processing the external API request.
    """
    request_data = await request.get_json()
    # TODO: Add additional request validation if required.
    job_id = str(uuid.uuid4())
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "data": None
    }
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, request_data))
    # Return the job ID so the client can later retrieve the results.
    return jsonify({"status": "processing", "job_id": job_id})


@app.route("/results", methods=["GET"])
async def get_results():
    """
    GET endpoint to retrieve stored job results.
    Returns the list of jobs and their data.
    """
    # For simplicity, we return all jobs.
    results = []
    for job_id, job_data in entity_jobs.items():
        entry = {"job_id": job_id}
        entry.update(job_data)
        results.append(entry)
    return jsonify({"status": "success", "results": results})


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)