import asyncio
import logging
import uuid
from datetime import datetime
from typing import List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema  # Schema initialization

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Initialize Quart app and QuartSchema
app = Quart(__name__)
QuartSchema(app)

# In-memory persistence (cache)
DATA_CACHE: List[dict] = []
ENTITY_JOBS = {}  # Stores processing job info keyed by job_id

# External API URL
CROCODILE_API_URL = "https://test-api.k6.io/public/crocodiles/"

async def process_entity(job_id: str, data: List[dict]):
    """
    Process the external data and load it into the in-memory database.
    TODO: Replace local cache with a persistent storage if needed.
    """
    try:
        # Simulate processing delay
        await asyncio.sleep(1)
        
        # Update in-memory cache (mock persistence)
        global DATA_CACHE
        DATA_CACHE.clear()
        DATA_CACHE.extend(data)
        
        # Mark the job as complete
        ENTITY_JOBS[job_id]["status"] = "complete"
        logger.info("Ingestion job %s completed, %d records ingested", job_id, len(data))
    except Exception as e:
        logger.exception(e)
        ENTITY_JOBS[job_id]["status"] = "failed"

@app.route("/api/crocodiles/ingest", methods=["POST"])
async def ingest_crocodiles():
    """
    Ingest crocodile data from the external API and store it into the in-memory cache.
    Returns a job ID for tracking the ingestion status.
    """
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat()
    ENTITY_JOBS[job_id] = {"status": "processing", "requestedAt": requested_at}
    logger.info("Starting ingestion job: %s", job_id)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(CROCODILE_API_URL)
            response.raise_for_status()
            data = response.json()

        # Fire and forget the processing task.
        # TODO: In a production system, consider using a background task handler
        await asyncio.create_task(process_entity(job_id, data))
        return jsonify({"message": "Data ingestion initiated", "job_id": job_id})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to ingest data"}), 500

@app.route("/api/crocodiles", methods=["GET"])
async def get_crocodiles():
    """
    Retrieve filtered crocodile data from the in-memory cache.
    Filtering parameters:
      - name: Filter by name (case-insensitive substring match)
      - sex: Filter by sex ('M' or 'F')
      - age_min: Minimum age (inclusive)
      - age_max: Maximum age (inclusive)
    """
    try:
        name = request.args.get("name", type=str)
        sex = request.args.get("sex", type=str)
        age_min = request.args.get("age_min", type=int)
        age_max = request.args.get("age_max", type=int)
    
        filtered = DATA_CACHE.copy()
    
        if name:
            filtered = [item for item in filtered if name.lower() in item.get("name", "").lower()]
        if sex:
            filtered = [item for item in filtered if item.get("sex") == sex]
        if age_min is not None:
            filtered = [item for item in filtered if item.get("age", 0) >= age_min]
        if age_max is not None:
            filtered = [item for item in filtered if item.get("age", 0) <= age_max]
    
        logger.info("Returning %d filtered records", len(filtered))
        return jsonify(filtered)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve data"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)