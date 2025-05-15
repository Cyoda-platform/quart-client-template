```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for crocodile data and ingestion jobs
# Structure: List of dicts for crocodiles
crocodile_cache: List[Dict] = []

# Track ingestion jobs status by job_id (simple counter-based id)
entity_job: Dict[int, Dict] = {}
job_counter = 0
job_lock = asyncio.Lock()


async def fetch_crocodiles_from_api() -> List[Dict]:
    url = "https://test-api.k6.io/public/crocodiles/"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            # According to API, data is a list of crocodiles
            if isinstance(data, list):
                return data
            else:
                logger.warning("Unexpected data format from external API")
                return []
        except httpx.HTTPError as e:
            logger.exception(f"HTTP error while fetching crocodiles: {e}")
            return []
        except Exception as e:
            logger.exception(f"Unexpected error while fetching crocodiles: {e}")
            return []


async def process_entity(job_id: int):
    """
    Fetch crocodiles from external API and store in local cache.
    Update job status accordingly.
    """
    try:
        crocodiles = await fetch_crocodiles_from_api()
        # Replace entire cache atomically
        global crocodile_cache
        # Critical section to avoid race conditions
        # Since crocodile_cache is a list, assign a new list
        crocodile_cache.clear()
        crocodile_cache.extend(crocodiles)

        entity_job[job_id]["status"] = "completed"
        entity_job[job_id]["ingested_count"] = len(crocodiles)
        entity_job[job_id]["completedAt"] = datetime.utcnow().isoformat() + "Z"
        logger.info(f"Ingestion job {job_id} completed: {len(crocodiles)} records ingested")
    except Exception as e:
        entity_job[job_id]["status"] = "failed"
        entity_job[job_id]["error"] = str(e)
        entity_job[job_id]["completedAt"] = datetime.utcnow().isoformat() + "Z"
        logger.exception(f"Ingestion job {job_id} failed")


@app.route("/crocodiles/ingest", methods=["POST"])
async def ingest_crocodiles():
    """
    Trigger ingestion from external API.
    Returns a job_id and status.
    """
    global job_counter
    async with job_lock:
        job_counter += 1
        job_id = job_counter
        requested_at = datetime.utcnow().isoformat() + "Z"
        entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}

    # Fire and forget ingestion process
    asyncio.create_task(process_entity(job_id))

    return jsonify({"message": "Data ingestion started", "job_id": job_id}), 202


def filter_crocodiles(
    data: List[Dict],
    name: Optional[str],
    sex: Optional[str],
    age_min: Optional[int],
    age_max: Optional[int],
) -> List[Dict]:
    """
    Filter crocodile list by optional parameters.
    - name: case-insensitive substring match
    - sex: exact match "M" or "F"
    - age_min, age_max: inclusive age range (assumes 'age' field is int)
    """
    filtered = []

    for croc in data:
        try:
            croc_name = croc.get("name", "")
            croc_sex = croc.get("sex", "").upper()
            croc_age = int(croc.get("age", -1))  # If missing or invalid, treated as -1

            if name and name.lower() not in croc_name.lower():
                continue
            if sex and sex.upper() != croc_sex:
                continue
            if age_min is not None and croc_age < age_min:
                continue
            if age_max is not None and croc_age > age_max:
                continue
            filtered.append(croc)
        except Exception:
            # Skip malformed entries, but log
            logger.warning(f"Skipping malformed crocodile entry: {croc}")
            continue

    return filtered


@app.route("/crocodiles", methods=["GET"])
async def get_crocodiles():
    """
    Retrieve crocodile data filtered by optional query parameters:
    - name (partial, case-insensitive)
    - sex (M or F)
    - age_min (integer)
    - age_max (integer)
    """
    params = request.args
    name = params.get("name")
    sex = params.get("sex")
    age_min = params.get("age_min")
    age_max = params.get("age_max")

    try:
        age_min_int = int(age_min) if age_min is not None else None
    except ValueError:
        return jsonify({"error": "Invalid age_min parameter"}), 400

    try:
        age_max_int = int(age_max) if age_max is not None else None
    except ValueError:
        return jsonify({"error": "Invalid age_max parameter"}), 400

    # Validate sex parameter if present
    if sex and sex.upper() not in ("M", "F"):
        return jsonify({"error": "Invalid sex parameter, must be 'M' or 'F'"}), 400

    filtered = filter_crocodiles(crocodile_cache, name, sex, age_min_int, age_max_int)
    return jsonify(filtered)


@app.route("/crocodiles/ingest/status/<int:job_id>", methods=["GET"])
async def ingestion_status(job_id: int):
    """
    Optional: Check status of ingestion job by job_id.
    """
    job = entity_job.get(job_id)
    if not job:
        return jsonify({"error": "Job ID not found"}), 404
    return jsonify(job)


if __name__ == '__main__':
    import sys
    import logging

    # Configure root logger to output to stdout
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
    )

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
