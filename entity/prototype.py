from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class CrocodileQuery:
    name: Optional[str] = None
    sex: Optional[str] = None
    min_age: Optional[int] = None
    max_age: Optional[int] = None

# In-memory cache for crocodile data and ingestion job statuses
class CrocodileStore:
    def __init__(self):
        self._data: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()

    async def update_data(self, new_data: List[Dict[str, Any]]):
        async with self._lock:
            self._data = new_data

    async def get_filtered(
        self,
        name: Optional[str] = None,
        sex: Optional[str] = None,
        min_age: Optional[int] = None,
        max_age: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        async with self._lock:
            filtered = self._data
            if name:
                filtered = [c for c in filtered if name.lower() in c.get("name", "").lower()]
            if sex in ("M", "F"):
                filtered = [c for c in filtered if c.get("sex") == sex]
            if min_age is not None:
                filtered = [c for c in filtered if isinstance(c.get("age"), (int, float)) and c.get("age") >= min_age]
            if max_age is not None:
                filtered = [c for c in filtered if isinstance(c.get("age"), (int, float)) and c.get("age") <= max_age]
            return filtered

crocodile_store = CrocodileStore()
entity_jobs: Dict[str, Dict[str, Any]] = {}
entity_jobs_lock = asyncio.Lock()

EXTERNAL_API_URL = "https://test-api.k6.io/public/crocodiles/"

async def fetch_external_crocodiles() -> List[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(EXTERNAL_API_URL, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            crocodiles = data.get("data")
            if isinstance(crocodiles, list):
                return crocodiles
            else:
                logger.warning("Unexpected data structure from external API")
                return []
        except Exception as e:
            logger.exception("Failed to fetch data from external API")
            return []

async def process_ingest_job(job_id: str):
    logger.info(f"Starting ingestion job {job_id}")
    try:
        crocodiles = await fetch_external_crocodiles()
        await crocodile_store.update_data(crocodiles)
        async with entity_jobs_lock:
            entity_jobs[job_id]["status"] = "completed"
            entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat() + "Z"
            entity_jobs[job_id]["ingested_count"] = len(crocodiles)
        logger.info(f"Ingestion job {job_id} completed successfully, {len(crocodiles)} records ingested")
    except Exception as e:
        logger.exception(f"Ingestion job {job_id} failed")
        async with entity_jobs_lock:
            entity_jobs[job_id]["status"] = "failed"
            entity_jobs[job_id]["error"] = str(e)

@app.route("/crocodiles/ingest", methods=["POST"])
async def ingest_crocodiles():
    """
    POST /crocodiles/ingest
    Trigger ingestion of crocodile data from external API.
    """
    job_id = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    job_info = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat() + "Z",
    }
    async with entity_jobs_lock:
        entity_jobs[job_id] = job_info

    # Fire and forget ingestion task
    asyncio.create_task(process_ingest_job(job_id))

    return jsonify({
        "status": "success",
        "message": "Ingestion job started",
        "job_id": job_id,
    })

# Workaround for quart-schema defect: place validate_querystring first for GET
@validate_querystring(CrocodileQuery)
@app.route("/crocodiles", methods=["GET"])
async def get_crocodiles():
    """
    GET /crocodiles?name=&sex=&min_age=&max_age=
    Retrieve filtered crocodile data.
    """
    params = request.args

    name = params.get("name")
    sex = params.get("sex")
    min_age_raw = params.get("min_age")
    max_age_raw = params.get("max_age")

    def parse_age(value: Optional[str]) -> Optional[int]:
        if value is None:
            return None
        try:
            v = int(value)
            if 0 <= v <= 200:
                return v
            else:
                return None
        except Exception:
            return None

    min_age = parse_age(min_age_raw)
    max_age = parse_age(max_age_raw)

    if sex is not None and sex not in ("M", "F"):
        return jsonify({"error": "Invalid sex parameter, must be 'M' or 'F'"}), 400

    filtered = await crocodile_store.get_filtered(name=name, sex=sex, min_age=min_age, max_age=max_age)
    return jsonify({
        "count": len(filtered),
        "results": filtered,
    })

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)