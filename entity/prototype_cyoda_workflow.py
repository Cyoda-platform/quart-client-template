from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import asyncio
import logging
from datetime import datetime

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

CAT_FACTS_API = "https://catfact.ninja/facts"
CAT_BREEDS_API = "https://api.thecatapi.com/v1/breeds"
CAT_IMAGES_API = "https://api.thecatapi.com/v1/images/search"

@dataclass
class FetchDataRequest:
    types: List[str]
    filters: Optional[Dict[str, Any]] = None

@dataclass
class FavoriteRequest:
    type: str
    content: str

# Workflow function for fetch_data entity
async def process_fetch_data(entity: Dict[str, Any]):
    """
    Asynchronously fetch cat facts, breeds, and images as requested.
    Modify the entity dict in-place to add fetched data under keys:
    'facts', 'breeds', 'images'.
    """
    requested_types = entity.get("types", [])
    filters = entity.get("filters") or {}

    async def fetch_cat_facts(limit: int = 5) -> List[str]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(CAT_FACTS_API, params={"limit": limit})
                resp.raise_for_status()
                data = resp.json()
                return [fact["fact"] for fact in data.get("data", [])]
        except Exception:
            logger.exception("Failed to fetch cat facts")
            return []

    async def fetch_cat_breeds(filter_breed: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(CAT_BREEDS_API)
                resp.raise_for_status()
                breeds = resp.json()
                if filter_breed:
                    breeds = [b for b in breeds if filter_breed.lower() in b.get("name", "").lower()]
                return [
                    {
                        "name": b.get("name"),
                        "origin": b.get("origin"),
                        "description": b.get("description")
                    }
                    for b in breeds
                ]
        except Exception:
            logger.exception("Failed to fetch cat breeds")
            return []

    async def fetch_cat_images(limit: int = 5) -> List[str]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(CAT_IMAGES_API, params={"limit": limit})
                resp.raise_for_status()
                images = resp.json()
                return [img.get("url") for img in images if img.get("url")]
        except Exception:
            logger.exception("Failed to fetch cat images")
            return []

    tasks = []
    if "facts" in requested_types:
        tasks.append(fetch_cat_facts())
    if "breeds" in requested_types:
        breed_filter = filters.get("breed")
        tasks.append(fetch_cat_breeds(breed_filter))
    if "images" in requested_types:
        tasks.append(fetch_cat_images())

    fetched_data = await asyncio.gather(*tasks)

    idx = 0
    if "facts" in requested_types:
        entity["facts"] = fetched_data[idx]
        idx += 1
    if "breeds" in requested_types:
        entity["breeds"] = fetched_data[idx]
        idx += 1
    if "images" in requested_types:
        entity["images"] = fetched_data[idx]
        idx += 1

    entity["processedAt"] = datetime.utcnow().isoformat()

    return entity

# Workflow function for favorite entity
async def process_favorite(entity: Dict[str, Any]):
    """
    Process favorite entity before persistence.
    Add timestamps and any validation flags.
    """
    entity["processedAt"] = datetime.utcnow().isoformat()
    entity.setdefault("isValid", True)
    return entity

@app.route("/cats/fetch-data", methods=["POST"])
@validate_request(FetchDataRequest)
async def cats_fetch_data(data: FetchDataRequest):
    """
    Endpoint calls entity_service.add_item with workflow.
    The workflow fetches and enriches data.
    """
    entity = data.__dict__
    try:
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="fetch_data",
            entity_version=ENTITY_VERSION,
            entity=entity,
            workflow=process_fetch_data
        )
        # Return enriched entity immediately after processing (before persistence completes might be possible)
        return jsonify(entity)
    except Exception:
        logger.exception("Error in /cats/fetch-data")
        return jsonify({"error": "Failed to fetch cat data"}), 500

@app.route("/cats/favorite", methods=["POST"])
@validate_request(FavoriteRequest)
async def cats_favorite(data: FavoriteRequest):
    """
    Endpoint validates input then persists favorite entity with workflow.
    """
    fav_type = data.type
    content = data.content

    if fav_type not in ("image", "fact") or not content:
        return jsonify({"error": "Invalid favorite submission"}), 400

    fav_record = {
        "type": fav_type,
        "content": content,
        "submittedAt": datetime.utcnow().isoformat()
    }

    try:
        fav_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="favorite",
            entity_version=ENTITY_VERSION,
            entity=fav_record,
            workflow=process_favorite
        )
        return jsonify({"status": "success", "message": "Favorite saved.", "id": fav_id})
    except Exception:
        logger.exception("Failed to save favorite")
        return jsonify({"error": "Failed to save favorite"}), 500

@app.route("/cats/results", methods=["GET"])
async def cats_results():
    """
    Returns latest cached cat data from entity_service.
    Queries latest fetch_data entity and returns requested data type.
    """
    try:
        data_type = request.args.get("type")
        valid_types = {"facts", "images", "breeds"}
        if data_type not in valid_types:
            return jsonify({"error": f"Invalid type '{data_type}'. Must be one of {valid_types}."}), 400

        # Query entity_service for latest fetch_data entity (assuming method get_latest_entity_by_model exists)
        # Adjust this according to your actual entity_service API
        latest_entity = await entity_service.get_latest_entity_by_model(
            token=cyoda_auth_service,
            entity_model="fetch_data",
            entity_version=ENTITY_VERSION
        )

        if not latest_entity:
            return jsonify({"type": data_type, "data": []})

        data = latest_entity.get(data_type, [])
        if data is None:
            data = []

        return jsonify({"type": data_type, "data": data})
    except Exception:
        logger.exception("Error in /cats/results")
        return jsonify({"error": "Failed to retrieve cat data"}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)