from dataclasses import dataclass
from typing import Optional, List
import asyncio
import logging

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# --- External API info ---
CAT_API_BASE = "https://api.thecatapi.com/v1"
CAT_API_BREEDS = f"{CAT_API_BASE}/breeds"
CAT_API_IMAGES_SEARCH = f"{CAT_API_BASE}/images/search"

@dataclass
class CatFetchTaskRequest:
    breed: Optional[str] = None
    limit: Optional[int] = 25

@dataclass
class BreedFetchTaskRequest:
    pass  # No parameters currently needed

@dataclass
class FetchCatsRequest:
    breed: Optional[str] = None  # For GET queries, not used in POST fetch task

# --- External API utilities ---

async def fetch_breeds() -> List[dict]:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(CAT_API_BREEDS, timeout=10.0)
            resp.raise_for_status()
            breeds = resp.json()
            normalized = []
            for b in breeds:
                normalized.append(
                    {
                        "id": b.get("id"),
                        "name": b.get("name"),
                        "description": b.get("description") or "",
                        "origin": b.get("origin") or "",
                    }
                )
            return normalized
        except Exception as e:
            logger.exception("Error fetching breeds: %s", e)
            return []

async def fetch_cats(breed: Optional[str] = None, limit: int = 25) -> List[dict]:
    async with httpx.AsyncClient() as client:
        try:
            params = {"limit": limit}
            if breed:
                params["breed_ids"] = breed

            resp = await client.get(CAT_API_IMAGES_SEARCH, params=params, timeout=10.0)
            resp.raise_for_status()
            images = resp.json()

            cats = []
            for img in images:
                breeds = img.get("breeds") or []
                breed_info = breeds[0] if breeds else {}
                cats.append(
                    {
                        "id": img.get("id"),
                        "name": breed_info.get("name", "Unknown"),
                        "image_url": img.get("url"),
                        "description": breed_info.get("description", ""),
                    }
                )
            return cats
        except Exception as e:
            logger.exception("Error fetching cats: %s", e)
            return []

# --- Workflow functions ---

async def process_cat(entity: dict):
    # Add or update timestamp to track when entity was processed
    import time
    entity['last_processed_at'] = time.time()
    # Additional enrichment or validation logic can be added here
    return entity

async def process_breed(entity: dict):
    import time
    entity['last_processed_at'] = time.time()
    return entity

async def process_cat_fetch_task(entity: dict):
    """
    Workflow to fetch cats from external API and add each cat entity asynchronously.
    """
    breed = entity.get("breed")
    limit = entity.get("limit")
    if limit is None or not isinstance(limit, int) or limit <= 0 or limit > 100:
        limit = 25  # default and max limit to prevent abuse

    cats = await fetch_cats(breed=breed, limit=limit)
    logger.info(f"Fetched {len(cats)} cats for breed={breed}")

    # Add each cat entity asynchronously with workflow=process_cat
    # Use asyncio.gather for concurrency but limit concurrency to avoid overload
    semaphore = asyncio.Semaphore(10)  # limit concurrent add_item calls

    async def add_cat_async(cat_data):
        async with semaphore:
            try:
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="cat",
                    entity_version=ENTITY_VERSION,
                    entity=cat_data,
                    workflow=process_cat,
                )
            except Exception as e:
                logger.exception("Failed to add cat entity: %s", e)

    await asyncio.gather(*(add_cat_async(cat) for cat in cats))

    # Mark task complete and add metadata before persistence
    entity['status'] = 'completed'
    entity['cats_fetched'] = len(cats)
    entity['completed_at'] = int(asyncio.get_event_loop().time() * 1000)
    return entity

async def process_breed_fetch_task(entity: dict):
    """
    Workflow to fetch breeds from external API and add each breed entity asynchronously.
    """
    breeds = await fetch_breeds()
    logger.info(f"Fetched {len(breeds)} breeds")

    semaphore = asyncio.Semaphore(10)

    async def add_breed_async(breed_data):
        async with semaphore:
            try:
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="breed",
                    entity_version=ENTITY_VERSION,
                    entity=breed_data,
                    workflow=process_breed,
                )
            except Exception as e:
                logger.exception("Failed to add breed entity: %s", e)

    await asyncio.gather(*(add_breed_async(breed) for breed in breeds))

    entity['status'] = 'completed'
    entity['breeds_fetched'] = len(breeds)
    entity['completed_at'] = int(asyncio.get_event_loop().time() * 1000)
    return entity

# --- Endpoints ---

@app.route("/cats/fetch", methods=["POST"])
@validate_request(CatFetchTaskRequest)
async def cats_fetch(data: CatFetchTaskRequest):
    """
    Endpoint to create a cat fetch task entity.
    The workflow on this entity will fetch cats and add them.
    """
    task_entity = data.__dict__
    try:
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="cat_fetch_task",
            entity_version=ENTITY_VERSION,
            entity=task_entity,
            workflow=process_cat_fetch_task,
        )
        return jsonify({
            "status": "success",
            "message": "Cat fetch task created",
            "entity_id": entity_id
        })
    except Exception as e:
        logger.exception("Error creating cat fetch task: %s", e)
        return jsonify({"error": "Failed to create cat fetch task"}), 500

@app.route("/cats", methods=["GET"])
async def cats_get():
    """
    Retrieve cats from entity service.
    """
    breed = request.args.get("breed")
    try:
        if breed:
            condition = {'name': breed}
            cats = await entity_service.get_items_by_condition(
                token=cyoda_auth_service,
                entity_model="cat",
                entity_version=ENTITY_VERSION,
                condition=condition,
            )
        else:
            cats = await entity_service.get_items(
                token=cyoda_auth_service,
                entity_model="cat",
                entity_version=ENTITY_VERSION,
            )
        return jsonify(cats)
    except Exception as e:
        logger.exception("Failed to retrieve cats: %s", e)
        return jsonify({"error": "Failed to retrieve cats"}), 500

@app.route("/cats/breeds/fetch", methods=["POST"])
@validate_request(BreedFetchTaskRequest)
async def breeds_fetch():
    """
    Endpoint to create a breed fetch task entity.
    Workflow will fetch breeds and add them.
    """
    task_entity = {}
    try:
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="breed_fetch_task",
            entity_version=ENTITY_VERSION,
            entity=task_entity,
            workflow=process_breed_fetch_task,
        )
        return jsonify({
            "status": "success",
            "message": "Breed fetch task created",
            "entity_id": entity_id
        })
    except Exception as e:
        logger.exception("Error creating breed fetch task: %s", e)
        return jsonify({"error": "Failed to create breed fetch task"}), 500

@app.route("/cats/breeds", methods=["GET"])
async def breeds_get():
    """
    Retrieve breeds from entity service.
    """
    try:
        breeds = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="breed",
            entity_version=ENTITY_VERSION,
        )
        return jsonify(breeds)
    except Exception as e:
        logger.exception("Failed to retrieve breeds: %s", e)
        return jsonify({"error": "Failed to retrieve breeds"}), 500

if __name__ == "__main__":
    import sys

    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)