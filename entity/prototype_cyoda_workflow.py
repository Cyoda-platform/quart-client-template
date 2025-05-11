from dataclasses import dataclass, field
from typing import Optional, Dict, Any

import logging
from datetime import datetime

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


@dataclass
class CatDataRequest:
    type: str
    filters: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class RandomCatRequest:
    includeImage: Optional[bool] = True


CAT_FACTS_API = "https://catfact.ninja/facts"
CAT_BREEDS_API = "https://api.thecatapi.com/v1/breeds"
CAT_IMAGES_API = "https://api.thecatapi.com/v1/images/search"

CAT_API_KEY = None
headers = {}
if CAT_API_KEY:
    headers["x-api-key"] = CAT_API_KEY


async def fetch_cat_facts(limit: int = 10):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(CAT_FACTS_API, params={"limit": limit})
            resp.raise_for_status()
            data = resp.json()
            return [fact["fact"] for fact in data.get("data", [])]
    except Exception as e:
        logger.exception("Error fetching cat facts: %s", e)
        return []


async def fetch_cat_breeds(limit: int = 10, breed_filter: Optional[str] = None):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(CAT_BREEDS_API, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            breeds = data
            if breed_filter:
                breeds = [b for b in breeds if breed_filter.lower() in b.get("name", "").lower()]
            return breeds[:limit]
    except Exception as e:
        logger.exception("Error fetching cat breeds: %s", e)
        return []


async def fetch_cat_images(limit: int = 10):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(CAT_IMAGES_API, headers=headers, params={"limit": limit})
            resp.raise_for_status()
            data = resp.json()
            return [img.get("url") for img in data if "url" in img]
    except Exception as e:
        logger.exception("Error fetching cat images: %s", e)
        return []


async def process_cat_data(entity):
    """
    Workflow function applied to the 'cat_data' entity before persistence.
    entity: dict with keys including 'type' and optional 'filters'.
    This function fetches the requested data asynchronously and updates the entity in-place.
    """
    try:
        data_type = entity.get("type")
        filters = entity.get("filters", {})
        limit = filters.get("limit", 10)
        if not isinstance(limit, int) or limit <= 0:
            limit = 10  # enforce sane default

        breed = filters.get("breed")

        if data_type == "facts":
            results = await fetch_cat_facts(limit)
        elif data_type == "breeds":
            results = await fetch_cat_breeds(limit, breed)
        elif data_type == "images":
            results = await fetch_cat_images(limit)
        else:
            results = []

        entity["results"] = results
        entity["last_updated"] = datetime.utcnow().isoformat()

        # Remove any previous error state if present
        entity.pop("error", None)

        logger.info(f"Workflow processed cat_data entity with type '{data_type}'")
    except Exception as e:
        logger.exception(f"Error in workflow process_cat_data: {e}")
        entity["error"] = str(e)


@app.route("/cats/data", methods=["POST"])
@validate_request(CatDataRequest)
async def post_cats_data(data: CatDataRequest):
    # Minimal controller: just add entity with workflow
    # Add a timestamp or unique id if needed for identification
    entity = {
        "type": data.type,
        "filters": data.filters or {},
        "requested_at": datetime.utcnow().isoformat()
    }

    try:
        entity_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="cat_data",
            entity_version=ENTITY_VERSION,
            entity=entity,
            workflow=process_cat_data  # workflow handles fetching & updating entity
        )
    except Exception as e:
        logger.exception(f"Failed to add cat_data entity: {e}")
        return jsonify({"status": "error", "message": "Failed to process request"}), 500

    return jsonify({"status": "processing", "entity_id": entity_id})


@app.route("/cats/results/<string:entity_id>", methods=["GET"])
async def get_cats_results(entity_id: str):
    try:
        item = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="cat_data",
            entity_version=ENTITY_VERSION,
            technical_id=entity_id
        )
        if not item:
            return jsonify({"status": "error", "message": "Data not found"}), 404

        return jsonify({
            "status": "success",
            "data": item
        })
    except Exception as e:
        logger.exception(f"Failed to retrieve cat_data entity {entity_id}: {e}")
        return jsonify({"status": "error", "message": "Failed to retrieve data"}), 500


@app.route("/cats/random", methods=["POST"])
@validate_request(RandomCatRequest)
async def post_cats_random(data: RandomCatRequest):
    include_image = data.includeImage if data.includeImage is not None else True

    try:
        facts = await fetch_cat_facts(1)
        fact = facts[0] if facts else "Cats are mysterious creatures."

        image_url = None
        if include_image:
            images = await fetch_cat_images(1)
            image_url = images[0] if images else None

        result = {"fact": fact}
        if image_url:
            result["image"] = image_url

        return jsonify({"status": "success", "cat": result})

    except Exception as e:
        logger.exception(f"Failed to fetch random cat: {e}")
        return jsonify({"status": "error", "message": "Failed to fetch random cat"}), 500


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)