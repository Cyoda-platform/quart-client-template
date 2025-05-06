Certainly! Below is a refactored version of your `routes.py` converted to use a `Blueprint` and fixing the import references to `entity_service` and `cyoda_token` according to your description and example. The main app logic, startup, and shutdown tasks are removed from this file as requested.

```python
# routes/routes.py

from common.grpc_client.grpc_client import grpc_stream
from dataclasses import dataclass
import logging
from datetime import datetime
import uuid
from quart import Blueprint, jsonify
from quart_schema import validate_request
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

routes_bp = Blueprint("routes", __name__)

# In-memory job status tracking dictionary
entity_job: dict = {}

CAT_FACT_API_URL = "https://catfact.ninja/fact"

@dataclass
class EmptyBody:
    pass

@routes_bp.route("/catfact/fetch", methods=["POST"])
@validate_request(EmptyBody)
async def fetch_catfact(data: EmptyBody):
    """
    POST endpoint to trigger fetching and storing a new cat fact.
    Creates minimal entity with job id to be processed by workflow function.
    """
    job_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat() + "Z"
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}

    # Minimal entity with _jobId for tracking inside workflow
    initial_entity = {"_jobId": job_id}

    try:
        entity_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="CatFact",
            entity_version=ENTITY_VERSION,
            entity=initial_entity,
        )
    except Exception as e:
        logger.exception(f"Failed to add CatFact entity: {e}")
        entity_job[job_id]["status"] = "failed"
        return jsonify({"status": "error", "message": "Failed to start cat fact fetch job"}), 500

    entity_job[job_id]["catFactId"] = entity_id

    return jsonify({
        "status": "success",
        "message": "Cat fact fetch job started",
        "jobId": job_id,
        "entityId": entity_id,
    }), 202

@routes_bp.route("/catfact/latest", methods=["GET"])
async def get_latest_catfact():
    """
    GET endpoint to retrieve the most recently fetched cat fact.
    """
    try:
        all_items = await entity_service.get_items(
            token=cyoda_token,
            entity_model="CatFact",
            entity_version=ENTITY_VERSION,
        )
        if not all_items:
            return jsonify({"error": "No cat facts stored yet"}), 404

        # Filter out entities missing 'fetchedAt' or with errors
        valid_items = [e for e in all_items if e.get("fetchedAt") and not e.get("error")]
        if not valid_items:
            return jsonify({"error": "No valid cat facts stored yet"}), 404

        latest_entity = max(valid_items, key=lambda e: e.get("fetchedAt", ""))
        return jsonify(latest_entity)
    except Exception as e:
        logger.exception(f"Failed to retrieve latest cat fact: {e}")
        return jsonify({"error": "Internal server error"}), 500

@routes_bp.route("/catfact/<string:catFactId>", methods=["GET"])
async def get_catfact(catFactId: str):
    """
    GET endpoint to retrieve a stored cat fact by its ID.
    """
    try:
        entity = await entity_service.get_item(
            token=cyoda_token,
            entity_model="CatFact",
            entity_version=ENTITY_VERSION,
            technical_id=catFactId,
        )
        if not entity:
            return jsonify({"error": "CatFact not found", "catFactId": catFactId}), 404
        if entity.get("error"):
            # Entity exists but processing failed
            return jsonify({"error": "CatFact processing failed", "catFactId": catFactId}), 500
        return jsonify(entity)
    except Exception as e:
        logger.exception(f"Failed to retrieve cat fact {catFactId}: {e}")
        return jsonify({"error": "Internal server error"}), 500

@routes_bp.route("/catfact/job/<string:jobId>", methods=["GET"])
async def get_job_status(jobId: str):
    """
    GET endpoint to check the status of a cat fact fetch job.
    """
    job = entity_job.get(jobId)
    if not job:
        return jsonify({"error": "Job not found", "jobId": jobId}), 404
    return jsonify(job)
```

---

### What was done:
- Replaced `app.route` decorators with `routes_bp.route` for all endpoints.
- Removed startup and shutdown logic (`before_serving`, `after_serving`) and `app` creation.
- Imported `cyoda_token` and `entity_service` directly from `app_init.app_init` as per your example.
- Kept all endpoint code and annotations intact in their original order and position.
- Added `routes_bp = Blueprint("routes", __name__)` at the top.
- You will need to register this blueprint in your `app.py`:

```python
from quart import Quart
from quart_schema import QuartSchema
from app_init.app_init import cyoda_token, entity_service
from common.repository.cyoda.cyoda_init import init_cyoda
import asyncio
from common.grpc_client.grpc_client import grpc_stream
from routes.routes import routes_bp

app = Quart(__name__)
QuartSchema(app)
app.register_blueprint(routes_bp)

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

# Your app run logic here...
```

---

If you want me to help with the `app.py` setup or any other part, just let me know!