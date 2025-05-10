from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Optional

import httpx
from quart import Quart, jsonify, request
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

entity_jobs = {}

THE_CAT_API_BREEDS_URL = "https://api.thecatapi.com/v1/breeds"
THE_CAT_API_IMAGES_URL = "https://api.thecatapi.com/v1/images/search"

@dataclass
class EmptyRequest:
    pass

# Workflow function for cat_breed entity
async def process_cat_breed(entity_data: dict) -> dict:
    """
    Workflow function applied to 'cat_breed' entities before persistence.
    
    Fetches image URL asynchronously from The Cat API for the breed and adds it.
    Adds a processed_at timestamp.
    """
    breed_id = entity_data.get("id")
    if not breed_id:
        logger.warning("No breed id found in entity_data during workflow processing.")
        return entity_data

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            params = {"breed_id": breed_id, "limit": 1}
            resp = await client.get(THE_CAT_API_IMAGES_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            if data and isinstance(data, list) and "url" in data[0]:
                entity_data["image_url"] = data[0]["url"]
            else:
                entity_data["image_url"] = ""
    except Exception as e:
        logger.warning(f"Failed to fetch image for breed {breed_id} inside workflow: {e}")
        entity_data["image_url"] = ""

    entity_data["processed_at"] = datetime.utcnow().isoformat()
    return entity_data

async def process_fetch_breeds_job(job_id: str):
    """
    Job that fetches all breeds from The Cat API and persists them using entity_service.
    """
    logger.info(f"Start processing job {job_id} to fetch breeds data")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(THE_CAT_API_BREEDS_URL)
            resp.raise_for_status()
            breeds = resp.json()

        # Delete old breeds
        existing_breeds = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="cat_breed",
            entity_version=ENTITY_VERSION,
        )
        for item in existing_breeds:
            try:
                await entity_service.delete_item(
                    token=cyoda_auth_service,
                    entity_model="cat_breed",
                    entity_version=ENTITY_VERSION,
                    technical_id=item.get("technical_id"),
                    meta={},
                )
            except Exception as e:
                logger.warning(f"Failed to delete old breed item {item.get('technical_id')}: {e}")

        # Add new breeds without image_url, workflow will enrich them
        for breed in breeds:
            breed_data = {
                "id": breed.get("id"),
                "name": breed.get("name", ""),
                "description": breed.get("description", ""),
            }
            try:
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="cat_breed",
                    entity_version=ENTITY_VERSION,
                    entity=breed_data,
                    workflow=process_cat_breed,
                )
            except Exception as e:
                logger.warning(f"Failed to add breed {breed.get('id')}: {e}")

        entity_jobs[job_id]["status"] = "completed"
        logger.info(f"Job {job_id} completed successfully")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        logger.exception(f"Job {job_id} failed: {e}")

@app.route("/api/cats/fetch-breeds", methods=["POST"])
@validate_request(EmptyRequest)
async def fetch_breeds(data: EmptyRequest):
    job_id = datetime.utcnow().isoformat() + "-job"
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    asyncio.create_task(process_fetch_breeds_job(job_id))
    return jsonify({"status": "processing", "job_id": job_id})

@app.route("/api/cats/breeds", methods=["GET"])
@validate_request(EmptyRequest)
async def get_all_breeds():
    try:
        breeds = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="cat_breed",
            entity_version=ENTITY_VERSION,
        )
        return jsonify(breeds)
    except Exception as e:
        logger.exception(f"Failed to get all breeds: {e}")
        return jsonify({"error": "Failed to retrieve breeds"}), 500

@app.route("/api/cats/breeds/<breed_id>", methods=["GET"])
async def get_breed_by_id(breed_id: str):
    try:
        condition = {"id": breed_id}
        items = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="cat_breed",
            entity_version=ENTITY_VERSION,
            condition=condition,
        )
        if not items:
            return jsonify({"error": "Breed not found"}), 404
        return jsonify(items[0])
    except Exception as e:
        logger.exception(f"Failed to get breed {breed_id}: {e}")
        return jsonify({"error": "Failed to retrieve breed"}), 500

@app.route("/api/cats/jobs/<job_id>", methods=["GET"])
async def get_job_status(job_id: str):
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)