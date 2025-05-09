Sure! I've updated the code to add the new `workflow` parameter to all `entity_service.add_item` calls, and implemented the required workflow functions with the prefix `process_` followed by the underscore lowercase entity name (`cat`, `adoption`, `health_check`). Each workflow function is async and takes the entity data as its only argument. They can update the entity state or add/get other entities as needed, following your specification.

Here is the complete updated code (only changed and relevant parts annotated with comments):

```python
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

# New workflow function for cat entity
async def process_cat(entity: dict) -> dict:
    # This function is applied to cat entity before persistence
    breed_name = entity.get("breed", "")
    if breed_name:
        breed_info = await fetch_breed_info(breed_name)
        if breed_info:
            entity["breed_info"] = {
                "origin": breed_info.get("origin"),
                "temperament": breed_info.get("temperament"),
                "description": breed_info.get("description")
            }
    # You can add more processing logic here if needed
    return entity

# New workflow function for adoption entity
async def process_adoption(entity: dict) -> dict:
    # Validate that cat exists and is available for adoption
    cat_id = entity.get("cat_id")
    if not cat_id:
        raise ValueError("cat_id is required in adoption entity")

    cat = await entity_service.get_item(
        token=cyoda_auth_service,
        entity_model="cat",
        entity_version=ENTITY_VERSION,
        technical_id=cat_id
    )
    if not cat:
        raise ValueError("Cat not found for adoption")

    if cat.get("state") != "Available":
        raise ValueError("Cat not available for adoption")

    # Set the adoption entity status and submitted_at timestamp
    entity["status"] = "Pending Approval"
    entity["submitted_at"] = datetime.utcnow().isoformat() + "Z"

    # Update cat state to Pending Adoption asynchronously (note: cannot update cat entity here because it's a different entity_model, so allowed)
    cat["state"] = "Pending Adoption"
    await entity_service.update_item(
        token=cyoda_auth_service,
        entity_model="cat",
        entity_version=ENTITY_VERSION,
        entity=cat,
        technical_id=cat_id,
        meta={}
    )

    return entity

# New workflow function for health_check entity
async def process_health_check(entity: dict) -> dict:
    cat_id = entity.get("cat_id")
    if not cat_id:
        raise ValueError("cat_id is required in health_check entity")

    health_status = entity.get("health_status", "").lower()

    # Get cat entity
    cat = await entity_service.get_item(
        token=cyoda_auth_service,
        entity_model="cat",
        entity_version=ENTITY_VERSION,
        technical_id=cat_id
    )
    if not cat:
        raise ValueError("Cat not found for health check")

    # Update cat state based on health_status
    if health_status != "healthy":
        cat["state"] = "Unavailable"
    else:
        if cat.get("state") == "Unavailable":
            cat["state"] = "Available"

    # Update cat entity asynchronously (allowed since different entity_model)
    await entity_service.update_item(
        token=cyoda_auth_service,
        entity_model="cat",
        entity_version=ENTITY_VERSION,
        entity=cat,
        technical_id=cat_id,
        meta={}
    )

    return entity

async def process_cat_creation_update(job_id: str, cat_data: dict):
    try:
        cat_id = cat_data.get("id")
        if not cat_id:
            # Add new cat with workflow
            cat_id = await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="cat",
                entity_version=ENTITY_VERSION,
                entity=cat_data,
                workflow=process_cat
            )
            cat_data["id"] = cat_id
        else:
            # Update existing cat (no workflow on update)
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="cat",
                entity_version=ENTITY_VERSION,
                entity=cat_data,
                technical_id=cat_id,
                meta={}
            )

        # Retrieve latest cat data to update result for job status
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

async def process_adoption_request(job_id: str, adoption_data: dict):
    try:
        adoption_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="adoption",
            entity_version=ENTITY_VERSION,
            entity=adoption_data,
            workflow=process_adoption
        )
        adoption_data["adoption_id"] = adoption_id

        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = adoption_data
        logger.info(f"Adoption request processed: {adoption_id}")

    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        logger.exception(e)

async def process_health_check(job_id: str, cat_id: str, health_data: dict):
    try:
        # Add or update health check record with workflow
        health_check_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="health_check",
            entity_version=ENTITY_VERSION,
            entity={"cat_id": cat_id, **health_data},
            workflow=process_health_check
        )

        health_status = health_data.get("health_status", "").lower()

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

    # Build condition for get_items_by_condition
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

    if conditions:
        try:
            if len(conditions) == 1:
                condition = conditions[0]
                cats = await entity_service.get_items_by_condition(
                    token=cyoda_auth_service,
                    entity_model="cat",
                    entity_version=ENTITY_VERSION,
                    condition=condition
                )
            else:
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
        except Exception as e:
            logger.exception(e)
            cats = []
    else:
        cats = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="cat",
            entity_version=ENTITY_VERSION
        )

    return jsonify(cats)

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
    adoption = await entity_service.get_item(
        token=cyoda_auth_service,
        entity_model="adoption",
        entity_version=ENTITY_VERSION,
        technical_id=adoption_id
    )
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
```

---

### Summary of changes:

- Added three async workflow functions:
  - `process_cat(entity: dict)`: enriches breed info before saving cat entity.
  - `process_adoption(entity: dict)`: verifies cat availability, updates cat state to pending adoption, and sets adoption entity fields.
  - `process_health_check(entity: dict)`: updates cat state based on health status after health check entity is added.

- Updated all calls to `entity_service.add_item` to pass the relevant workflow function as the `workflow` parameter.

- No changes to `update_item` calls since the workflow function applies only on add_item.

This matches your new requirement and keeps existing logic intact. Let me know if you want me to explain or adjust anything!