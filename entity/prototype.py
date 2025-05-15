from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache and job tracking
crocodile_cache: List[Dict] = []
entity_job: Dict[int, Dict] = {}
job_counter = 0
job_lock = asyncio.Lock()

@dataclass
class IngestRequest:
    # no fields required for ingestion trigger
    pass

@dataclass
class CrocodileQuery:
    name: Optional[str] = None
    sex: Optional[str] = None
    age_min: Optional[int] = None
    age_max: Optional[int] = None

async def fetch_crocodiles_from_api() -> List[Dict]:
    url = "https://test-api.k6.io/public/crocodiles/"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else []
        except httpx.HTTPError as e:
            logger.exception(f"HTTP error while fetching crocodiles: {e}")
            return []
        except Exception as e:
            logger.exception(f"Unexpected error while fetching crocodiles: {e}")
            return []

async def process_entity(job_id: int):
    try:
        crocodiles = await fetch_crocodiles_from_api()
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
@validate_request(IngestRequest)  # validation last for POST due to Quart-Schema defect
async def ingest_crocodiles(data: IngestRequest):
    global job_counter
    async with job_lock:
        job_counter += 1
        job_id = job_counter
        entity_job[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat() + "Z"}
    asyncio.create_task(process_entity(job_id))
    return jsonify({"message": "Data ingestion started", "job_id": job_id}), 202

@validate_querystring(CrocodileQuery)  # workaround: validation first for GET due to Quart-Schema defect
@app.route("/crocodiles", methods=["GET"])
async def get_crocodiles():
    name = request.args.get("name")
    sex = request.args.get("sex")
    age_min = request.args.get("age_min")
    age_max = request.args.get("age_max")

    try:
        age_min_int = int(age_min) if age_min is not None else None
    except ValueError:
        return jsonify({"error": "Invalid age_min parameter"}), 400
    try:
        age_max_int = int(age_max) if age_max is not None else None
    except ValueError:
        return jsonify({"error": "Invalid age_max parameter"}), 400

    if sex and sex.upper() not in ("M", "F"):
        return jsonify({"error": "Invalid sex parameter, must be 'M' or 'F'"}), 400

    def filter_crocodiles(data: List[Dict], name, sex, age_min, age_max):
        result = []
        for croc in data:
            try:
                if name and name.lower() not in croc.get("name", "").lower():
                    continue
                if sex and sex.upper() != croc.get("sex", "").upper():
                    continue
                age = int(croc.get("age", -1))
                if age_min is not None and age < age_min:
                    continue
                if age_max is not None and age > age_max:
                    continue
                result.append(croc)
            except Exception:
                logger.warning(f"Skipping malformed entry: {croc}")
        return result

    filtered = filter_crocodiles(crocodile_cache, name, sex, age_min_int, age_max_int)
    return jsonify(filtered)

@app.route("/crocodiles/ingest/status/<int:job_id>", methods=["GET"])
async def ingestion_status(job_id: int):
    job = entity_job.get(job_id)
    if not job:
        return jsonify({"error": "Job ID not found"}), 404
    return jsonify(job)

if __name__ == '__main__':
    import sys
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)