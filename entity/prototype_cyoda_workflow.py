from dataclasses import dataclass, field
from typing import Optional, Dict, Any

import asyncio
import logging
from datetime import datetime
import uuid

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)


@dataclass
class CatDataRequestFilters:
    breed: Optional[str] = None
    limit: Optional[int] = 10


@dataclass
class CatDataRequest:
    type: str
    filters: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class CatPhotoSubmission:
    user_id: str
    photo_url: str
    description: Optional[str] = None


# In-memory local cache for job tracking
entity_job: Dict[str, Dict[str, Any]] = {}
last_results_cache: Dict[str, Any] = {"data": []}

CAT_FACT_API = "https://catfact.ninja/fact"
CAT_BREEDS_API = "https://api.thecatapi.com/v1/breeds"
CAT_IMAGES_API = "https://api.thecatapi.com/v1/images/search"


async def fetch_cat_fact(client: httpx.AsyncClient) -> Dict[str, Any]:
    resp = await client.get(CAT_FACT_API)
    resp.raise_for_status()
    data = resp.json()
    return {"fact": data.get("fact")}


async def fetch_cat_breeds(client: httpx.AsyncClient, limit: int = 10, breed_filter: str = None) -> Any:
    resp = await client.get(CAT_BREEDS_API)
    resp.raise_for_status()
    breeds = resp.json()
    if breed_filter:
        breeds = [b for b in breeds if breed_filter.lower() in b.get("name", "").lower()]
    return breeds[:limit]


async def fetch_cat_images(client: httpx.AsyncClient, limit: int = 1) -> Any:
    params = {"limit": limit}
    resp = await client.get(CAT_IMAGES_API, params=params)
    resp.raise_for_status()
    return resp.json()


async def process_entity(job: Dict[str, Any], data: Dict[str, Any]):
    try:
        job["status"] = "processing"
        job["startedAt"] = datetime.utcnow().isoformat()
        async with httpx.AsyncClient(timeout=10) as client:
            cat_type = data.get("type")
            filters = data.get("filters", {})
            limit = filters.get("limit", 10)
            breed = filters.get("breed")

            if cat_type == "facts":
                results = []
                for _ in range(limit):
                    fact = await fetch_cat_fact(client)
                    results.append(fact)
            elif cat_type == "breeds":
                results = await fetch_cat_breeds(client, limit=limit, breed_filter=breed)
            elif cat_type == "images":
                results = await fetch_cat_images(client, limit=limit)
            else:
                results = []
                logger.warning(f"Unknown type requested: {cat_type}")

            last_results_cache["data"] = results
            job["status"] = "completed"
            job["completedAt"] = datetime.utcnow().isoformat()
            job["resultCount"] = len(results)
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        logger.exception(e)


async def process_cat_data_request(entity: Dict[str, Any]):
    job_id = entity.get("job_id")
    if not job_id:
        job_id = str(uuid.uuid4())
        entity["job_id"] = job_id

    # Prevent overwriting existing job accidentally
    if job_id not in entity_job:
        entity_job[job_id] = {
            "status": "queued",
            "createdAt": datetime.utcnow().isoformat(),
            "entity": entity,
        }
    else:
        # If job already exists, do not reset or overwrite status to avoid conflicts
        logger.warning(f"Job {job_id} already exists in entity_job cache.")

    # Fire-and-forget async processing task
    asyncio.create_task(process_entity(entity_job[job_id], entity))


async def process_cat_photo_submission(entity: Dict[str, Any]):
    if "submittedAt" not in entity:
        entity["submittedAt"] = datetime.utcnow().isoformat()
    # Additional processing or enrichment can be added here as needed
    logger.info(f"Processing cat_photo_submission for user {entity.get('user_id')}")


@app.route("/api/cats/data", methods=["POST"])
@validate_request(CatDataRequest)
async def post_cat_data(data: CatDataRequest):
    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="cat_data_request",
            entity_version=ENTITY_VERSION,
            entity=data.__dict__,
            workflow=process_cat_data_request
        )
        return jsonify({"status": "accepted", "id": id}), 202
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/cats/results", methods=["GET"])
async def get_cat_results():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="cat_data_result",
            entity_version=ENTITY_VERSION
        )
        return jsonify({"status": "success", "data": items})
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/cats/submit-photo", methods=["POST"])
@validate_request(CatPhotoSubmission)
async def post_cat_photo(data: CatPhotoSubmission):
    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="cat_photo_submission",
            entity_version=ENTITY_VERSION,
            entity=data.__dict__,
            workflow=process_cat_photo_submission
        )
        return jsonify({"status": "success", "id": id})
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)