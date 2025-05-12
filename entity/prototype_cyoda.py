from dataclasses import dataclass
from typing import Optional, Dict, List
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

# Entity job tracking (simulate async job processing)
entity_jobs: Dict[str, Dict] = {}

@dataclass
class Filters:
    breed: Optional[str] = None
    limit: Optional[int] = 10

@dataclass
class Search:
    breed: Optional[str] = None
    name: Optional[str] = None

@dataclass
class LiveDataRequest:
    filters: Optional[Filters] = None

@dataclass
class SearchRequest:
    search: Optional[Search] = None


async def fetch_live_cat_data(filters: Dict) -> List[Dict]:
    """
    Fetch live cat data from real external API.
    We'll use TheCatAPI (https://thecatapi.com/) for breeds and images.
    For fun facts, we'll use a placeholder (TODO).
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
            "id": breed.get("id"),
            "name": breed.get("name"),
            "breed": breed.get("name"),
            "image_url": None,
            "fact": None,
        }

        # Fetch image for breed if available
        # TheCatAPI provides image in breed info sometimes
        image = breed.get("image")
        if image and image.get("url"):
            cat["image_url"] = image["url"]
        else:
            # Try to get an image by breed ID separately
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

        # TODO: Replace with real cat fact API or database
        # For now, use a static fun fact or empty string
        cat["fact"] = f"{cat['breed']} is a wonderful cat breed!"

        cats_data.append(cat)

    return cats_data


async def process_live_data_job(job_id: str, filters: Dict):
    """
    Background task to fetch live data and store using entity_service.
    """
    logger.info(f"Processing job {job_id} with filters: {filters}")
    try:
        cats = await fetch_live_cat_data(filters)

        # Instead of caching locally, store each cat item in entity_service
        # Clear previous cats? Since we have no delete all, we skip that step to keep logic simpler.

        # Store cats asynchronously, but we'll await all to complete
        tasks = []
        for cat in cats:
            # Remove 'id' key from cat because entity_service will generate its own id
            cat_data = cat.copy()
            cat_data.pop("id", None)
            tasks.append(
                entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="cat",
                    entity_version=ENTITY_VERSION,
                    entity=cat_data,
                )
            )
        # Await all add_item calls, but result ids are not used here
        await asyncio.gather(*tasks)

        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result_count"] = len(cats)
        entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
        logger.info(f"Job {job_id} completed with {len(cats)} cats")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        logger.exception(f"Job {job_id} failed: {e}")

# POST /cats/live-data
@app.route("/cats/live-data", methods=["POST"])
@validate_request(LiveDataRequest)  # validation last on POST endpoints (issue workaround)
async def post_live_data(data: LiveDataRequest):
    filters = data.filters.__dict__ if data.filters else {}

    job_id = datetime.utcnow().isoformat()  # simple job id, can be improved
    entity_jobs[job_id] = {"status": "processing", "requestedAt": job_id}

    # Fire and forget processing task
    asyncio.create_task(process_live_data_job(job_id, filters))

    return jsonify({"job_id": job_id, "status": "processing"}), 202


# GET /cats - fetch cats from entity_service
@app.route("/cats", methods=["GET"])
async def get_cats():
    """
    Return cats data from entity_service.
    """
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


# POST /cats/search
@app.route("/cats/search", methods=["POST"])
@validate_request(SearchRequest)  # validation last on POST endpoints (issue workaround)
async def post_cats_search(data: SearchRequest):
    search = data.search.__dict__ if data.search else {}
    breed_filter = search.get("breed")
    name_filter = search.get("name")

    # Build condition for entity_service - since entity_service supports condition queries
    # We will build a simple condition dict that the service can understand.
    # Assuming condition is a dict with keys and values for equality or substring match

    # Since entity_service condition is not fully defined, if insufficient, skip and fallback to local filter

    if breed_filter or name_filter:
        # Construct condition with substring matching if possible, else skip
        # Since no detailed condition format is described, we'll skip and fallback to get_items and filter locally
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
    else:
        # No filters, return all cats
        try:
            results = await entity_service.get_items(
                token=cyoda_auth_service,
                entity_model="cat",
                entity_version=ENTITY_VERSION,
            )
        except Exception as e:
            logger.exception(e)
            return jsonify({"error": "Failed to retrieve cats"}), 500

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