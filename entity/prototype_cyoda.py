from dataclasses import dataclass
from typing import Optional
import asyncio
import logging
from datetime import datetime

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

# Data models for POST requests
@dataclass
class CatDataRequest:
    source: Optional[str] = "all"
    dataType: Optional[str] = "all"

# Track entity jobs
entity_jobs = {}

# External APIs (real)
CAT_FACTS_API = "https://catfact.ninja/fact"
CAT_BREEDS_API = "https://api.thecatapi.com/v1/breeds"
CAT_IMAGES_API = "https://api.thecatapi.com/v1/images/search"


async def fetch_cat_fact(client: httpx.AsyncClient) -> Optional[str]:
    try:
        r = await client.get(CAT_FACTS_API)
        r.raise_for_status()
        data = r.json()
        return data.get("fact")
    except Exception as e:
        logger.exception(f"Failed to fetch cat fact: {e}")
        return None


async def fetch_cat_breeds(client: httpx.AsyncClient) -> list:
    try:
        r = await client.get(CAT_BREEDS_API)
        r.raise_for_status()
        data = r.json()
        # Extract relevant info
        breeds = []
        for breed in data:
            breeds.append({
                "name": breed.get("name"),
                "origin": breed.get("origin"),
                "description": breed.get("description")
            })
        return breeds
    except Exception as e:
        logger.exception(f"Failed to fetch cat breeds: {e}")
        return []


async def fetch_cat_images(client: httpx.AsyncClient, limit: int = 5) -> list:
    try:
        params = {"limit": limit}
        r = await client.get(CAT_IMAGES_API, params=params)
        r.raise_for_status()
        data = r.json()
        # Extract URLs
        images = [item.get("url") for item in data if item.get("url")]
        return images
    except Exception as e:
        logger.exception(f"Failed to fetch cat images: {e}")
        return []


async def process_entity(job_id: str, source: str, data_type: str):
    """Background task to fetch and update data."""
    logger.info(f"Started processing job {job_id} for source={source}, dataType={data_type}")
    async with httpx.AsyncClient(timeout=10) as client:
        count = 0

        if data_type in ("facts", "all"):
            fact = await fetch_cat_fact(client)
            if fact:
                try:
                    # Add fact entity
                    await entity_service.add_item(
                        token=cyoda_auth_service,
                        entity_model="cat_fact",
                        entity_version=ENTITY_VERSION,
                        entity={"fact": fact}
                    )
                    count += 1
                except Exception as e:
                    logger.exception(f"Failed to add cat fact entity: {e}")

        if data_type in ("breeds", "all"):
            breeds = await fetch_cat_breeds(client)
            if breeds:
                try:
                    # For breeds, update by deleting existing and adding new (no local cache)
                    existing_breeds = await entity_service.get_items(
                        token=cyoda_auth_service,
                        entity_model="cat_breed",
                        entity_version=ENTITY_VERSION,
                    )
                    # Delete existing breeds
                    for item in existing_breeds:
                        try:
                            await entity_service.delete_item(
                                token=cyoda_auth_service,
                                entity_model="cat_breed",
                                entity_version=ENTITY_VERSION,
                                technical_id=item.get("technicalId"),
                                meta={}
                            )
                        except Exception as e:
                            logger.exception(f"Failed to delete cat breed entity: {e}")
                    # Add new breeds
                    for breed in breeds:
                        try:
                            await entity_service.add_item(
                                token=cyoda_auth_service,
                                entity_model="cat_breed",
                                entity_version=ENTITY_VERSION,
                                entity=breed
                            )
                        except Exception as e:
                            logger.exception(f"Failed to add cat breed entity: {e}")
                    count += len(breeds)
                except Exception as e:
                    logger.exception(f"Failed to update cat breeds entities: {e}")

        if data_type in ("images", "all"):
            images = await fetch_cat_images(client, limit=5)
            if images:
                try:
                    # Similar to breeds, delete existing images and add new
                    existing_images = await entity_service.get_items(
                        token=cyoda_auth_service,
                        entity_model="cat_image",
                        entity_version=ENTITY_VERSION,
                    )
                    for item in existing_images:
                        try:
                            await entity_service.delete_item(
                                token=cyoda_auth_service,
                                entity_model="cat_image",
                                entity_version=ENTITY_VERSION,
                                technical_id=item.get("technicalId"),
                                meta={}
                            )
                        except Exception as e:
                            logger.exception(f"Failed to delete cat image entity: {e}")
                    for url in images:
                        try:
                            await entity_service.add_item(
                                token=cyoda_auth_service,
                                entity_model="cat_image",
                                entity_version=ENTITY_VERSION,
                                entity={"url": url}
                            )
                        except Exception as e:
                            logger.exception(f"Failed to add cat image entity: {e}")
                    count += len(images)
                except Exception as e:
                    logger.exception(f"Failed to update cat images entities: {e}")

    entity_jobs[job_id]["status"] = "completed"
    entity_jobs[job_id]["fetchedDataCount"] = count
    entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
    logger.info(f"Completed processing job {job_id}, fetched {count} items.")


# POST /cats/data
@app.route("/cats/data", methods=["POST"])
@validate_request(CatDataRequest)  # Validation last in POST method (issue workaround)
async def update_cat_data(data: CatDataRequest):
    source = data.source or "all"
    data_type = data.dataType or "all"

    job_id = datetime.utcnow().isoformat() + "_job"
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "fetchedDataCount": 0,
        "completedAt": None,
    }

    # Fire and forget background task
    asyncio.create_task(process_entity(job_id, source, data_type))

    return jsonify({
        "status": "success",
        "message": f"Data update triggered for dataType={data_type}",
        "jobId": job_id,
    })


# GET /cats/facts - retrieve facts from entity_service
@app.route("/cats/facts", methods=["GET"])
async def get_cat_facts():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="cat_fact",
            entity_version=ENTITY_VERSION,
        )
        # Extract facts from entities
        facts = [item.get("fact") for item in items if item.get("fact")]
        return jsonify({"facts": facts})
    except Exception as e:
        logger.exception(f"Failed to get cat facts: {e}")
        return jsonify({"facts": []}), 500


# GET /cats/images - retrieve images from entity_service
@app.route("/cats/images", methods=["GET"])
async def get_cat_images():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="cat_image",
            entity_version=ENTITY_VERSION,
        )
        images = [item.get("url") for item in items if item.get("url")]
        return jsonify({"images": images})
    except Exception as e:
        logger.exception(f"Failed to get cat images: {e}")
        return jsonify({"images": []}), 500


# GET /cats/breeds - retrieve breeds from entity_service
@app.route("/cats/breeds", methods=["GET"])
async def get_cat_breeds():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="cat_breed",
            entity_version=ENTITY_VERSION,
        )
        breeds = []
        for item in items:
            breed = {
                "name": item.get("name"),
                "origin": item.get("origin"),
                "description": item.get("description")
            }
            breeds.append(breed)
        return jsonify({"breeds": breeds})
    except Exception as e:
        logger.exception(f"Failed to get cat breeds: {e}")
        return jsonify({"breeds": []}), 500


if __name__ == '__main__':
    import sys
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
        stream=sys.stdout,
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)