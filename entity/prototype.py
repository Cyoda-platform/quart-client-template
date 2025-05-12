```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Simple in-memory cache to store fetched cats data
cached_cats: List[Dict] = []

# Entity job tracking (simulate async job processing)
entity_jobs: Dict[str, Dict] = {}


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
    Background task to fetch live data and store in cache.
    """
    logger.info(f"Processing job {job_id} with filters: {filters}")
    try:
        cats = await fetch_live_cat_data(filters)
        # Update global cache (overwrite)
        global cached_cats
        cached_cats = cats

        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result_count"] = len(cats)
        entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
        logger.info(f"Job {job_id} completed with {len(cats)} cats")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        logger.exception(f"Job {job_id} failed: {e}")


@app.route("/cats/live-data", methods=["POST"])
async def post_live_data():
    """
    POST /cats/live-data
    Request JSON: {"filters": {"breed": str (optional), "limit": int (optional)}}
    Response: cats list fetched live, also cached internally
    """
    data = await request.get_json(force=True)
    filters = data.get("filters", {})

    job_id = datetime.utcnow().isoformat()  # simple job id, can be improved
    entity_jobs[job_id] = {"status": "processing", "requestedAt": job_id}

    # Fire and forget processing task
    asyncio.create_task(process_live_data_job(job_id, filters))

    return jsonify({"job_id": job_id, "status": "processing"}), 202


@app.route("/cats", methods=["GET"])
async def get_cats():
    """
    GET /cats
    Return the cached cats data.
    """
    return jsonify({"cats": cached_cats})


@app.route("/cats/search", methods=["POST"])
async def post_cats_search():
    """
    POST /cats/search
    Request JSON: {"search": {"breed": str (optional), "name": str (optional)}}
    Response: filtered cats list from cached data
    """
    data = await request.get_json(force=True)
    search = data.get("search", {})
    breed_filter = search.get("breed")
    name_filter = search.get("name")

    def matches(cat):
        if breed_filter and breed_filter.lower() not in cat["breed"].lower():
            return False
        if name_filter and name_filter.lower() not in cat["name"].lower():
            return False
        return True

    results = [cat for cat in cached_cats if matches(cat)]

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
```
