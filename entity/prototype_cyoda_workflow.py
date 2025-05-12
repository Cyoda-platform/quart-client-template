from dataclasses import dataclass
from typing import Optional, Dict, List, Any
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

@dataclass
class Filters:
    breed: Optional[str] = None
    limit: Optional[int] = 10

@dataclass
class LiveDataRequest:
    filters: Optional[Filters] = None

@dataclass
class Search:
    breed: Optional[str] = None
    name: Optional[str] = None

@dataclass
class SearchRequest:
    search: Optional[Search] = None


async def fetch_live_cat_data(filters: Dict) -> List[Dict]:
    """
    Fetch live cat data from TheCatAPI.
    """
    limit = filters.get("limit", 10)
    breed_filter = filters.get("breed")

    breeds_url = "https://api.thecatapi.com/v1/breeds"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(breeds_url, timeout=10)
            response.raise_for_status()
            breeds = response.json()
        except Exception as e:
            logger.exception(f"Error fetching breeds from TheCatAPI: {e}")
            return []

    # Filter breeds if filter specified
    if breed_filter:
        breeds = [b for b in breeds if breed_filter.lower() in b["name"].lower()]

    # Limit results
    breeds = breeds[:limit]

    cats_data = []
    for breed in breeds:
        cat = {
            "name": breed.get("name"),
            "breed": breed.get("name"),
            "image_url": None,
            "fact": None,
        }

        # Fetch image for breed if available
        image = breed.get("image")
        if image and image.get("url"):
            cat["image_url"] = image["url"]
        else:
            try:
                async with httpx.AsyncClient() as client:
                    img_resp = await client.get(
                        f"https://api.thecatapi.com/v1/images/search?breed_id={breed['id']}&limit=1", timeout=10
                    )
                    img_resp.raise_for_status()
                    imgs = img_resp.json()
                    if imgs and imgs[0].get("url"):
                        cat["image_url"] = imgs[0]["url"]
            except Exception as e:
                logger.exception(f"Error fetching image for breed {breed['id']}: {e}")

        # Static fun fact placeholder
        cat["fact"] = f"{cat['breed']} is a wonderful cat breed!"

        cats_data.append(cat)

    return cats_data


async def process_cat(entity: Dict) -> Dict:
    """
    Workflow function for 'cat' entity.
    Enrich cat entity before persistence.
    """
    name = entity.get("name")
    breed = entity.get("breed")

    if not breed and name:
        entity["breed"] = name

    if not entity.get("image_url") and breed:
        try:
            async with httpx.AsyncClient() as client:
                breeds_resp = await client.get("https://api.thecatapi.com/v1/breeds", timeout=10)
                breeds_resp.raise_for_status()
                breeds = breeds_resp.json()
                breed_id = None
                for b in breeds:
                    if b["name"].lower() == breed.lower():
                        breed_id = b["id"]
                        break
                if breed_id:
                    img_resp = await client.get(
                        f"https://api.thecatapi.com/v1/images/search?breed_id={breed_id}&limit=1", timeout=10
                    )
                    img_resp.raise_for_status()
                    imgs = img_resp.json()
                    if imgs and imgs[0].get("url"):
                        entity["image_url"] = imgs[0]["url"]
        except Exception as e:
            logger.warning(f"Failed to enrich cat image_url: {e}")

    if not entity.get("fact") and entity.get("breed"):
        entity["fact"] = f"{entity['breed']} is a wonderful cat breed!"

    return entity


async def process_cat_live_data_fetch_request(entity: Dict) -> Dict:
    """
    Workflow function for 'cat_live_data_fetch_request' entity.
    Fetches live cat data and adds multiple 'cat' entities.
    Updates the job status in this entity.
    """
    filters = entity.get("filters", {}) or {}
    job_started_at = datetime.utcnow().isoformat()
    entity["status"] = "processing"
    entity["requestedAt"] = job_started_at

    try:
        cats = await fetch_live_cat_data(filters)

        for cat in cats:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="cat",
                entity_version=ENTITY_VERSION,
                entity=cat,
                workflow=process_cat,
            )

        entity["status"] = "completed"
        entity["result_count"] = len(cats)
        entity["completedAt"] = datetime.utcnow().isoformat()
    except Exception as e:
        entity["status"] = "failed"
        entity["error"] = str(e)
        logger.exception(f"Failed to process cat_live_data_fetch_request: {e}")

    return entity


@app.route("/cats/live-data", methods=["POST"])
@validate_request(LiveDataRequest)
async def post_live_data(data: LiveDataRequest):
    filters = data.filters.__dict__ if data.filters else {}

    entity = {
        "filters": filters,
    }

    entity_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model="cat_live_data_fetch_request",
        entity_version=ENTITY_VERSION,
        entity=entity,
        workflow=process_cat_live_data_fetch_request,
    )

    return jsonify({"job_id": entity_id, "status": "processing"}), 202


@app.route("/cats", methods=["GET"])
async def get_cats():
    try:
        cats = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="cat",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve cats"}), 500

    return jsonify({"cats": cats})


@app.route("/cats/search", methods=["POST"])
@validate_request(SearchRequest)
async def post_cats_search(data: SearchRequest):
    search = data.search.__dict__ if data.search else {}
    breed_filter = search.get("breed")
    name_filter = search.get("name")

    try:
        cats = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="cat",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve cats"}), 500

    def matches(cat):
        if breed_filter and breed_filter.lower() not in (cat.get("breed") or "").lower():
            return False
        if name_filter and name_filter.lower() not in (cat.get("name") or "").lower():
            return False
        return True

    results = [cat for cat in cats if matches(cat)]

    return jsonify({"results": results})


if __name__ == "__main__":
    import sys
    import logging.config

    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        level=logging.INFO,
        stream=sys.stdout,
    )

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)