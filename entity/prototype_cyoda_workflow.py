import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

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

entity_jobs: Dict[str, Dict] = {}

CAT_API_BASE = "https://api.thecatapi.com/v1"
CAT_FACTS_API = "https://catfact.ninja/fact"


@dataclass
class LiveDataRequest:
    dataType: str
    filters: Optional[dict] = None


@dataclass
class FavoriteRequest:
    userId: str
    favoriteType: str
    favoriteId: str


# --- Workflow functions ---


async def process_cat_image(entity: dict) -> dict:
    # Add processed timestamp
    entity['processed_at'] = datetime.utcnow().isoformat()
    return entity


async def process_cat_breed(entity: dict) -> dict:
    # Normalize breed name to title case
    if 'name' in entity and isinstance(entity['name'], str):
        entity['name'] = entity['name'].title()
    return entity


async def process_cat_fact(entity: dict) -> dict:
    # Append a source field
    entity['source'] = 'catfact.ninja'
    return entity


async def process_cat_favorite(entity: dict) -> dict:
    # Add created timestamp
    entity['created_at'] = datetime.utcnow().isoformat()

    fav_type = entity.get("type")
    fav_id = entity.get("favorite_id")
    try:
        if fav_type == "image":
            img_items = await entity_service.get_items_by_condition(
                token=cyoda_auth_service,
                entity_model="cat_image",
                entity_version=ENTITY_VERSION,
                condition={"id": fav_id}
            )
            if img_items:
                img = img_items[0]
                entity["image_info"] = {
                    "id": img.get("id"),
                    "url": img.get("url"),
                    "breed": img.get("breed"),
                }
        elif fav_type == "breed":
            breed_items = await entity_service.get_items_by_condition(
                token=cyoda_auth_service,
                entity_model="cat_breed",
                entity_version=ENTITY_VERSION,
                condition={"id": fav_id}
            )
            if breed_items:
                breed = breed_items[0]
                entity["breed_info"] = {
                    "id": breed.get("id"),
                    "name": breed.get("name"),
                    "origin": breed.get("origin"),
                    "description": breed.get("description"),
                }
    except Exception:
        logger.exception(f"Failed to enrich favorite entity {entity}")

    return entity


async def process_live_data(entity: dict) -> dict:
    # This workflow handles fetching and persisting requested live data
    data_type = entity.get("dataType")
    filters = entity.get("filters", {})

    job_id = entity.get("jobId") or f"job_{datetime.utcnow().timestamp()}"
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "dataType": data_type,
        "filters": filters,
    }

    logger.info(f"Live data workflow started for job {job_id}: {data_type} with filters={filters}")

    try:
        if data_type == "images":
            limit = filters.get("limit", 10)
            breed = filters.get("breed")
            images = await fetch_cat_images(limit=limit, breed=breed)
            for img in images:
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="cat_image",
                    entity_version=ENTITY_VERSION,
                    entity=img,
                    workflow=process_cat_image
                )
            count = len(images)

        elif data_type == "breeds":
            limit = filters.get("limit", 10)
            breeds = await fetch_cat_breeds(limit=limit)
            for breed in breeds:
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="cat_breed",
                    entity_version=ENTITY_VERSION,
                    entity=breed,
                    workflow=process_cat_breed
                )
            count = len(breeds)

        elif data_type == "facts":
            limit = filters.get("limit", 5)
            facts = await fetch_cat_facts(limit=limit)
            for fact_text in facts:
                fact_entity = {"fact": fact_text}
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="cat_fact",
                    entity_version=ENTITY_VERSION,
                    entity=fact_entity,
                    workflow=process_cat_fact
                )
            count = len(facts)

        else:
            entity_jobs[job_id]["status"] = "failed"
            entity_jobs[job_id]["message"] = f"Unknown dataType: {data_type}"
            logger.warning(f"Unknown dataType in live data workflow: {data_type}")
            return entity

        entity_jobs[job_id].update({
            "status": "completed",
            "count": count,
            "completedAt": datetime.utcnow().isoformat(),
        })
        logger.info(f"Live data workflow completed for job {job_id}: {count} items")

    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["message"] = str(e)
        logger.exception(f"Error in live data workflow for job {job_id}: {e}")

    entity["jobId"] = job_id
    return entity


# --- Helper async fetch functions used in workflows ---


async def fetch_cat_images(limit: int = 10, breed: Optional[str] = None) -> List[Dict]:
    params = {"limit": limit}
    if breed:
        params["breed_ids"] = breed
    headers = {"x-api-key": ""}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{CAT_API_BASE}/images/search", params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data:
                breed_name = item["breeds"][0]["name"] if item.get("breeds") else None
                results.append({
                    "id": item["id"],
                    "url": item["url"],
                    "breed": breed_name,
                })
            return results
        except Exception as e:
            logger.exception(f"Failed to fetch cat images: {e}")
            return []


async def fetch_cat_breeds(limit: int = 10) -> List[Dict]:
    headers = {"x-api-key": ""}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{CAT_API_BASE}/breeds", headers=headers)
            resp.raise_for_status()
            data = resp.json()
            breeds = []
            for item in data[:limit]:
                breeds.append({
                    "id": item["id"],
                    "name": item["name"],
                    "origin": item.get("origin", ""),
                    "description": item.get("description", ""),
                })
            return breeds
        except Exception as e:
            logger.exception(f"Failed to fetch cat breeds: {e}")
            return []


async def fetch_cat_facts(limit: int = 5) -> List[str]:
    facts = []
    async with httpx.AsyncClient() as client:
        try:
            for _ in range(limit):
                resp = await client.get(CAT_FACTS_API)
                resp.raise_for_status()
                data = resp.json()
                fact = data.get("fact")
                if fact:
                    facts.append(fact)
            return facts
        except Exception as e:
            logger.exception(f"Failed to fetch cat facts: {e}")
            return []


# --- Endpoints ---


@app.route("/cats/live-data", methods=["POST"])
@validate_request(LiveDataRequest)  # Validation last in POST (workaround issue)
async def post_live_data(data: LiveDataRequest):
    entity = {
        "dataType": data.dataType,
        "filters": data.filters or {},
    }

    entity_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="live_data",
        entity_version=ENTITY_VERSION,
        entity=entity,
        workflow=process_live_data
    )

    return jsonify({
        "status": "success",
        "message": "Data fetch started",
        "entityId": entity_id,
    })


@app.route("/cats/images", methods=["GET"])
async def get_cat_images():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="cat_image",
            entity_version=ENTITY_VERSION,
        )
        return jsonify({"images": items})
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": "Failed to fetch cat images"}), 500


@app.route("/cats/breeds", methods=["GET"])
async def get_cat_breeds():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="cat_breed",
            entity_version=ENTITY_VERSION,
        )
        return jsonify({"breeds": items})
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": "Failed to fetch cat breeds"}), 500


@app.route("/cats/facts", methods=["GET"])
async def get_cat_facts():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="cat_fact",
            entity_version=ENTITY_VERSION,
        )
        facts = [item.get("fact") for item in items if "fact" in item]
        return jsonify({"facts": facts})
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": "Failed to fetch cat facts"}), 500


@app.route("/cats/favorites", methods=["POST"])
@validate_request(FavoriteRequest)  # Validation last in POST (workaround issue)
async def post_favorites(data: FavoriteRequest):
    favorite_obj = {
        "user_id": data.userId,
        "type": data.favoriteType,
        "favorite_id": data.favoriteId,
    }

    try:
        fav_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="cat_favorite",
            entity_version=ENTITY_VERSION,
            entity=favorite_obj,
            workflow=process_cat_favorite
        )
        return jsonify({"status": "success", "message": "Favorite saved", "id": fav_id})
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": "Failed to save favorite"}), 500


@app.route("/cats/favorites", methods=["GET"])
async def get_favorites():
    user_id = request.args.get("userId")
    if not user_id:
        return jsonify({"status": "error", "message": "Missing userId query parameter"}), 400

    try:
        condition = {"user_id": user_id}
        favs = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="cat_favorite",
            entity_version=ENTITY_VERSION,
            condition=condition
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": "Failed to fetch favorites"}), 500

    return jsonify({"favorites": favs})


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)