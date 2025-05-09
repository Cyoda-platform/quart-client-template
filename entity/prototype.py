from dataclasses import dataclass, field
from typing import Optional
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
import asyncio
import logging
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

cats_store = {}
adoptions_store = {}
health_checks_store = {}
entity_jobs = {}

def generate_id(prefix: str) -> str:
    return f"{prefix}{int(datetime.utcnow().timestamp() * 1000)}"

CAT_API_BASE = "https://api.thecatapi.com/v1"
CAT_API_KEY = None  # TODO: Add your API key here if available

@dataclass
class CatFilter:
    state: Optional[str] = None
    breed: Optional[str] = None
    age: Optional[int] = None

@dataclass
class CatData:
    id: Optional[str] = None
    name: str = ""
    breed: str = ""
    age: int = 0
    health_status: str = ""
    state: str = ""

@dataclass
class AdoptionData:
    cat_id: str
    applicant_name: str
    contact_info: str

@dataclass
class HealthCheckData:
    check_date: str
    health_status: str
    notes: Optional[str] = ""

async def fetch_breed_info(breed_name: str):
    headers = {}
    if CAT_API_KEY:
        headers["x-api-key"] = CAT_API_KEY
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{CAT_API_BASE}/breeds/search?q={breed_name}", headers=headers)
            resp.raise_for_status()
            data = resp.json()
            if data:
                return data[0]
            return {}
        except Exception as e:
            logger.exception(f"Error fetching breed info for {breed_name}: {e}")
            return {}

async def process_cat_creation_update(job_id: str, cat_data: dict):
    try:
        breed_name = cat_data.get("breed", "")
        breed_info = await fetch_breed_info(breed_name) if breed_name else {}

        if breed_info:
            cat_data["breed_info"] = {
                "origin": breed_info.get("origin"),
                "temperament": breed_info.get("temperament"),
                "description": breed_info.get("description")
            }

        cat_id = cat_data.get("id")
        if not cat_id:
            cat_id = generate_id("cat")
            cat_data["id"] = cat_id
        cats_store[cat_id] = cat_data

        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = cat_data
        logger.info(f"Cat record processed successfully: {cat_id}")

    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        logger.exception(e)

async def process_adoption_request(job_id: str, adoption_data: dict):
    try:
        cat_id = adoption_data.get("cat_id")
        cat = cats_store.get(cat_id)
        if not cat:
            raise ValueError("Cat not found")
        if cat.get("state") != "Available":
            raise ValueError("Cat not available for adoption")

        cat["state"] = "Pending Adoption"
        cats_store[cat_id] = cat

        adoption_id = generate_id("adopt")
        adoption_record = {
            "adoption_id": adoption_id,
            "cat_id": cat_id,
            "applicant_name": adoption_data.get("applicant_name"),
            "contact_info": adoption_data.get("contact_info"),
            "status": "Pending Approval",
            "submitted_at": datetime.utcnow().isoformat() + "Z"
        }
        adoptions_store[adoption_id] = adoption_record

        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = adoption_record
        logger.info(f"Adoption request processed: {adoption_id}")

    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        logger.exception(e)

async def process_health_check(job_id: str, cat_id: str, health_data: dict):
    try:
        cat = cats_store.get(cat_id)
        if not cat:
            raise ValueError("Cat not found")

        health_checks_store[cat_id] = health_data

        health_status = health_data.get("health_status", "").lower()
        if health_status != "healthy":
            cat["state"] = "Unavailable"
        else:
            if cat.get("state") == "Unavailable":
                cat["state"] = "Available"
        cats_store[cat_id] = cat

        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = {"cat_id": cat_id, "health_status": health_status}
        logger.info(f"Health check processed for cat: {cat_id}")

    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        logger.exception(e)

# GET /cats with validation first (workaround for quart-schema issue)
@app.route("/cats", methods=["GET"])
@validate_querystring(CatFilter)  # validation first for GET (workaround)
async def list_cats():
    state = request.args.get("state")
    breed = request.args.get("breed")
    age = request.args.get("age")

    results = []
    for cat in cats_store.values():
        if state and cat.get("state") != state:
            continue
        if breed and cat.get("breed") != breed:
            continue
        if age:
            try:
                age_int = int(age)
                if cat.get("age") != age_int:
                    continue
            except:
                pass
        results.append(cat)
    return jsonify(results)

# POST /cats with validation last (workaround for quart-schema issue)
@app.route("/cats", methods=["POST"])  # route first
@validate_request(CatData)           # validation last for POST (workaround)
async def create_update_cat(data: CatData):
    requested_at = datetime.utcnow().isoformat() + "Z"
    job_id = generate_id("job")
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}

    asyncio.create_task(process_cat_creation_update(job_id, data.__dict__))

    return jsonify({"success": True, "job_id": job_id, "message": "Cat creation/update processing started"}), 202

# GET /cats/job/<job_id> no validation needed
@app.route("/cats/job/<job_id>", methods=["GET"])
async def get_cat_job_status(job_id):
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)

# POST /adoptions validation last for POST
@app.route("/adoptions", methods=["POST"])
@validate_request(AdoptionData)
async def submit_adoption(data: AdoptionData):
    requested_at = datetime.utcnow().isoformat() + "Z"
    job_id = generate_id("job")
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}

    asyncio.create_task(process_adoption_request(job_id, data.__dict__))

    return jsonify({"success": True, "job_id": job_id, "message": "Adoption request processing started"}), 202

# GET /adoptions/<adoption_id> no validation needed
@app.route("/adoptions/<adoption_id>", methods=["GET"])
async def get_adoption_status(adoption_id):
    adoption = adoptions_store.get(adoption_id)
    if not adoption:
        return jsonify({"error": "Adoption not found"}), 404
    return jsonify(adoption)

# POST /cats/<cat_id>/health-check validation last for POST
@app.route("/cats/<cat_id>/health-check", methods=["POST"])
@validate_request(HealthCheckData)
async def update_health_check(cat_id, data: HealthCheckData):
    requested_at = datetime.utcnow().isoformat() + "Z"
    job_id = generate_id("job")
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}

    asyncio.create_task(process_health_check(job_id, cat_id, data.__dict__))

    return jsonify({"success": True, "job_id": job_id, "message": "Health check processing started"}), 202

# GET /cats/<cat_id> no validation needed
@app.route("/cats/<cat_id>", methods=["GET"])
async def get_cat(cat_id):
    cat = cats_store.get(cat_id)
    if not cat:
        return jsonify({"error": "Cat not found"}), 404
    return jsonify(cat)

if __name__ == '__main__':
    import sys
    import logging.config

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s - %(message)s',
        stream=sys.stdout,
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```