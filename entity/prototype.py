import asyncio
import uuid
from datetime import datetime
from dataclasses import dataclass

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request

# Initialize Quart app and schema
app = Quart(__name__)
QuartSchema(app)

# Global in-memory storage and job tracking (mock persistence)
STORAGE = {"crocodiles": []}
INGESTION_JOBS = {}

EXTERNAL_API_URL = "https://test-api.k6.io/public/crocodiles/"

# Dummy dataclass for ingestion endpoint (no payload expected)
@dataclass
class IngestRequest:
    # This is a dummy field to satisfy the validate_request decorator.
    dummy: str = ""

# Dataclass for filter endpoint
@dataclass
class FilterCrocodilesRequest:
    # Using only primitives per instructions. Note: Using min_age and max_age instead of nested age_range.
    name: str = ""
    sex: str = ""
    min_age: int = 0
    max_age: int = 200

async def process_entity(job_id: str, data):
    # TODO: Add any processing logic if needed.
    # Simulate processing delay
    await asyncio.sleep(1)
    # In this prototype, we simply store the data in our in-memory STORAGE.
    if isinstance(data, list):
        STORAGE["crocodiles"] = data
    else:
        # TODO: Handle unexpected data formats from the external API.
        STORAGE["crocodiles"] = []
    INGESTION_JOBS[job_id]["status"] = "done"
    INGESTION_JOBS[job_id]["completedAt"] = datetime.utcnow().isoformat()

@app.route('/api/crocodiles/ingest', methods=['POST'])
@validate_request(IngestRequest)  # Workaround: For POST endpoints, validate_request is added after route declaration.
async def ingest_crocodiles(data: IngestRequest):
    # Retrieve data from the external API using aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(EXTERNAL_API_URL) as resp:
            # TODO: Add error handling for non-200 responses
            external_data = await resp.json()

    # Create a job to process the data asynchronously
    job_id = str(uuid.uuid4())
    INGESTION_JOBS[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(job_id, external_data))
    ingested_count = len(external_data) if isinstance(external_data, list) else 0
    return jsonify({
        "status": "success",
        "message": "Data ingestion initiated.",
        "job_id": job_id,
        "ingested_count": ingested_count
    })

@app.route('/api/crocodiles/filter', methods=['POST'])
@validate_request(FilterCrocodilesRequest)  # Workaround: For POST endpoints, validate_request is added after route declaration.
async def filter_crocodiles(data: FilterCrocodilesRequest):
    # Apply filtering on the in-memory STORAGE using validated data from request
    name_filter = data.name.lower() if data.name else ""
    sex_filter = data.sex if data.sex else ""
    min_age = data.min_age
    max_age = data.max_age

    results = []
    for crocodile in STORAGE.get("crocodiles", []):
        # Assume each crocodile is a dict with keys: 'name', 'sex', 'age'
        # TODO: Validate data format of each record.
        match = True
        if name_filter and name_filter not in crocodile.get("name", "").lower():
            match = False
        if sex_filter and crocodile.get("sex") != sex_filter:
            match = False
        age = crocodile.get("age")
        if age is None or not (min_age <= age <= max_age):
            match = False
        if match:
            results.append(crocodile)

    return jsonify({
        "status": "success",
        "results": results
    })

@app.route('/api/crocodiles/results', methods=['GET'])
async def get_all_crocodiles():
    return jsonify({
        "status": "success",
        "data": STORAGE.get("crocodiles", [])
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)