from dataclasses import dataclass, field
from typing import Optional
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
import asyncio
import logging
from datetime import datetime
import httpx
from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

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

async def process_cat_job(job_id: str, cat_data: dict):
    try:
        cat_id = cat_data.get("id")
        if cat_id:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="cat",
                entity_version=ENTITY_VERSION,
                entity=cat_data,
                technical_id=cat_id,
                meta={}
            )
        else:
            cat_id = await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="cat",
                entity_version=ENTITY_VERSION,
                entity=cat_data,
                )
            cat_data["id"] = cat_id
        cat = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="cat",
            entity_version=ENTITY_VERSION,
            technical_id=cat_id
        )
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = cat
        logger.info(f"Cat record processed successfully: {cat_id}")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        logger.exception(e)

async def process_adoption_job(job_id: str, adoption_data: dict):
    try:
        adoption_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="adoption",
            entity_version=ENTITY_VERSION,
            entity=adoption_data,
            )
        adoption_data["adoption_id"] = adoption_id
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = adoption_data
        logger.info(f"Adoption request processed: {adoption_id}")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        logger.exception(e)

async def process_health_check_job(job_id: str, cat_id: str, health_data: dict):
    try:
        health_check_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="health_check",
            entity_version=ENTITY_VERSION,
            entity={"cat_id": cat_id, **health_data},
            )
        health_status = health_data.get("health_status", "").lower()
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = {"cat_id": cat_id, "health_status": health_status}
        logger.info(f"Health check processed for cat: {cat_id}")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        logger.exception(e)

@app.route("/cats", methods=["GET"])
@validate_querystring(CatFilter)
async def list_cats():
    state = request.args.get("state")
    breed = request.args.get("breed")
    age = request.args.get("age")
    conditions = []
    if state:
        conditions.append({"field": "state", "op": "=", "value": state})
    if breed:
        conditions.append({"field": "breed", "op": "=", "value": breed})
    if age:
        try:
            age_int = int(age)
            conditions.append({"field": "age", "op": "=", "value": age_int})
        except:
            pass
    try:
        if len(conditions) == 1:
            condition = conditions[0]
            cats = await entity_service.get_items_by_condition(
                token=cyoda_auth_service,
                entity_model="cat",
                entity_version=ENTITY_VERSION,
                condition=condition
            )
        elif len(conditions) > 1:
            cats_all = await entity_service.get_items(
                token=cyoda_auth_service,
                entity_model="cat",
                entity_version=ENTITY_VERSION
            )
            cats = []
            for cat in cats_all:
                match = True
                for cond in conditions:
                    field = cond["field"]
                    val = cond["value"]
                    if cat.get(field) != val:
                        match = False
                        break
                if match:
                    cats.append(cat)
        else:
            cats = await entity_service.get_items(
                token=cyoda_auth_service,
                entity_model="cat",
                entity_version=ENTITY_VERSION
            )
    except Exception as e:
        logger.exception(e)
        cats = []
    return jsonify(cats)

@app.route("/cats", methods=["POST"])
@validate_request(CatData)
async def create_update_cat(data: CatData):
    requested_at = datetime.utcnow().isoformat() + "Z"
    job_id = generate_id("job")
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}
    asyncio.create_task(process_cat_job(job_id, data.__dict__))
    return jsonify({"success": True, "job_id": job_id, "message": "Cat creation/update processing started"}), 202

@app.route("/cats/job/<job_id>", methods=["GET"])
async def get_cat_job_status(job_id):
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)

@app.route("/adoptions", methods=["POST"])
@validate_request(AdoptionData)
async def submit_adoption(data: AdoptionData):
    requested_at = datetime.utcnow().isoformat() + "Z"
    job_id = generate_id("job")
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}
    asyncio.create_task(process_adoption_job(job_id, data.__dict__))
    return jsonify({"success": True, "job_id": job_id, "message": "Adoption request processing started"}), 202

@app.route("/adoptions/<adoption_id>", methods=["GET"])
async def get_adoption_status(adoption_id):
    adoption = await entity_service.get_item(
        token=cyoda_auth_service,
        entity_model="adoption",
        entity_version=ENTITY_VERSION,
        technical_id=adoption_id
    )
    if not adoption:
        return jsonify({"error": "Adoption not found"}), 404
    return jsonify(adoption)

@app.route("/cats/<cat_id>/health-check", methods=["POST"])
@validate_request(HealthCheckData)
async def update_health_check(cat_id, data: HealthCheckData):
    requested_at = datetime.utcnow().isoformat() + "Z"
    job_id = generate_id("job")
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}
    asyncio.create_task(process_health_check_job(job_id, cat_id, data.__dict__))
    return jsonify({"success": True, "job_id": job_id, "message": "Health check processing started"}), 202

@app.route("/cats/<cat_id>", methods=["GET"])
async def get_cat(cat_id):
    cat = await entity_service.get_item(
        token=cyoda_auth_service,
        entity_model="cat",
        entity_version=ENTITY_VERSION,
        technical_id=cat_id
    )
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