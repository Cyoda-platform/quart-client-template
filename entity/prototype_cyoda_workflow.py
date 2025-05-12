from dataclasses import dataclass
from typing import Dict, Optional

import logging
from datetime import datetime
from typing import List

import httpx
from quart import Quart, jsonify
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

# External API base URLs for real live cat data
CAT_FACTS_API = "https://catfact.ninja/facts"
CAT_BREEDS_API = "https://api.thecatapi.com/v1/breeds"
CAT_IMAGES_API = "https://api.thecatapi.com/v1/images/search"


@dataclass
class LiveDataRequest:
    data_type: str
    filters: Optional[Dict] = None


@dataclass
class FavoriteRequest:
    cat_id: str
    user_id: Optional[str] = None


@app.route("/cats/live-data", methods=["POST"])
@validate_request(LiveDataRequest)
async def post_live_data(data: LiveDataRequest):
    try:
        job_id = datetime.utcnow().isoformat()
        entity_data = {
            "job_id": job_id,
            "status": "queued",
            "requestedAt": job_id,
            "data_type": data.data_type,
            "filters": data.filters or {},
        }
        # Add entity with workflow that will perform async fetching and enrich entity before persistence
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            entity=entity_data,
            workflow=process_entity_job
        )
        return jsonify({"status": "processing", "job_id": job_id, "id": id})
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/cats/latest", methods=["GET"])
async def get_latest():
    try:
        condition = {
            "data_type": "random",
            "status": "done"
        }
        results = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="entity_job",
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        if results:
            sorted_results = sorted(
                results,
                key=lambda x: x.get("processed_at", ""),
                reverse=True
            )
            latest = sorted_results[0].get("result", [])
        else:
            latest = []
        return jsonify({"status": "success", "data": latest})
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/cats/favorites", methods=["POST"])
@validate_request(FavoriteRequest)
async def post_favorite(data: FavoriteRequest):
    try:
        if not data.cat_id:
            return jsonify({"status": "error", "message": "Missing cat_id"}), 400

        favorite_data = {
            "cat_id": data.cat_id,
            "user_id": data.user_id,
            "added_at": datetime.utcnow().isoformat()
        }

        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="favorite_cats",
            entity_version=ENTITY_VERSION,
            entity=favorite_data,
            workflow=process_favorite_cats
        )
        return jsonify({"status": "success", "message": "Cat added to favorites", "id": id})
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/cats/favorites", methods=["GET"])
async def get_favorites():
    try:
        favorites = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="favorite_cats",
            entity_version=ENTITY_VERSION
        )
        return jsonify({"status": "success", "data": favorites})
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500


# --- Workflow functions ---


async def fetch_cat_facts(filters: Optional[Dict]) -> List[Dict]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(CAT_FACTS_API)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
    except Exception as e:
        logger.exception(e)
        return []


async def fetch_cat_breeds(filters: Optional[Dict]) -> List[Dict]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(CAT_BREEDS_API)
            response.raise_for_status()
            breeds = response.json()
            if filters and "breed" in filters:
                filtered = [
                    b for b in breeds
                    if filters["breed"].lower() in b.get("name", "").lower()
                ]
                return filtered
            else:
                return breeds
    except Exception as e:
        logger.exception(e)
        return []


async def fetch_cat_images(filters: Optional[Dict]) -> List[Dict]:
    try:
        params = {"limit": 5}
        if filters and "breed" in filters:
            breeds = await fetch_cat_breeds({"breed": filters["breed"]})
            if breeds:
                breed_id = breeds[0].get("id")
                if breed_id:
                    params["breed_id"] = breed_id

        async with httpx.AsyncClient() as client:
            response = await client.get(CAT_IMAGES_API, params=params)
            response.raise_for_status()
            images = response.json()
            return images
    except Exception as e:
        logger.exception(e)
        return []


async def process_entity_job(entity: Dict) -> Dict:
    try:
        entity["status"] = "processing"
        data_type = entity.get("data_type")
        filters = entity.get("filters", {})

        if data_type == "facts":
            data = await fetch_cat_facts(filters)
        elif data_type == "breeds":
            data = await fetch_cat_breeds(filters)
        elif data_type == "images":
            data = await fetch_cat_images(filters)
        elif data_type == "random":
            facts = await fetch_cat_facts(filters)
            images = await fetch_cat_images(filters)
            breeds = await fetch_cat_breeds(filters)
            data = {
                "facts": facts[:3],
                "images": images[:3],
                "breeds": breeds[:3],
            }
        else:
            data = []

        entity["result"] = data
        entity["processed_at"] = datetime.utcnow().isoformat()
        entity["status"] = "done"
        entity["workflow_processed_at"] = datetime.utcnow().isoformat()

    except Exception as e:
        logger.exception(e)
        entity["status"] = "error"
        entity["error"] = str(e)

    return entity


async def process_favorite_cats(entity: Dict) -> Dict:
    try:
        entity["workflow_processed_at"] = datetime.utcnow().isoformat()
        # Potential place to enrich favorite cat entity or fetch supplementary data
    except Exception as e:
        logger.exception(e)
        entity["error"] = str(e)
    return entity


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)