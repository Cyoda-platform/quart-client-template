```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for favorites and async job tracking
favorites_cache: Dict[str, Dict[str, Any]] = {}
entity_job: Dict[str, Dict[str, Any]] = {}

CAT_API_BASE = "https://api.thecatapi.com/v1"
CAT_API_KEY = ""  # TODO: Insert your The Cat API key here or leave empty for limited access


async def fetch_random_cats(count: int = 1) -> Any:
    headers = {"x-api-key": CAT_API_KEY} if CAT_API_KEY else {}
    async with httpx.AsyncClient() as client:
        try:
            params = {"limit": count}
            resp = await client.get(f"{CAT_API_BASE}/images/search", headers=headers, params=params)
            resp.raise_for_status()
            images = resp.json()

            # Fetch facts from another source or mock facts (TheCatAPI does not provide facts)
            # TODO: Replace with real cat facts API or service if available
            facts = [
                "Cats sleep 70% of their lives.",
                "Cats have five toes on their front paws, but only four toes on their back paws.",
                "Cats can rotate their ears 180 degrees."
            ]

            cats = []
            for i, img in enumerate(images):
                cats.append({
                    "id": img.get("id"),
                    "image_url": img.get("url"),
                    "fact": facts[i % len(facts)]
                })
            return {"cats": cats}
        except Exception as e:
            logger.exception(e)
            return {"cats": []}


async def fetch_cats_by_breed(breed: str, count: int = 1) -> Any:
    headers = {"x-api-key": CAT_API_KEY} if CAT_API_KEY else {}
    async with httpx.AsyncClient() as client:
        try:
            # Fetch breed list to get breed id
            breed_resp = await client.get(f"{CAT_API_BASE}/breeds", headers=headers)
            breed_resp.raise_for_status()
            breeds = breed_resp.json()
            breed_id = None
            for b in breeds:
                if b["name"].lower() == breed.lower():
                    breed_id = b["id"]
                    break
            if not breed_id:
                return {"cats": []}  # Breed not found

            # Fetch images by breed id
            params = {"breed_ids": breed_id, "limit": count}
            img_resp = await client.get(f"{CAT_API_BASE}/images/search", headers=headers, params=params)
            img_resp.raise_for_status()
            images = img_resp.json()

            # TODO: Replace with real facts per breed if available
            breed_fact = f"The {breed} cat is a lovely breed."

            cats = []
            for img in images:
                cats.append({
                    "id": img.get("id"),
                    "breed": breed,
                    "image_url": img.get("url"),
                    "fact": breed_fact
                })
            return {"cats": cats}
        except Exception as e:
            logger.exception(e)
            return {"cats": []}


async def process_add_favorite(job_id: str, cat_data: Dict[str, Any]) -> None:
    try:
        # Simulate processing delay
        await asyncio.sleep(0.1)
        cat_id = cat_data.get("cat_id") or cat_data.get("id") or str(datetime.utcnow().timestamp())
        favorites_cache[cat_id] = cat_data
        entity_job[job_id]["status"] = "completed"
        logger.info(f"Added favorite cat id={cat_id}")
    except Exception as e:
        entity_job[job_id]["status"] = "failed"
        logger.exception(e)


@app.route('/cats/random', methods=["POST"])
async def post_cats_random():
    data = await request.get_json(force=True, silent=True) or {}
    count = data.get("count", 1)
    result = await fetch_random_cats(count)
    return jsonify(result)


@app.route('/cats/breed', methods=["POST"])
async def post_cats_breed():
    data = await request.get_json(force=True, silent=True) or {}
    breed = data.get("breed", "")
    count = data.get("count", 1)
    if not breed:
        return jsonify({"cats": []}), 400
    result = await fetch_cats_by_breed(breed, count)
    return jsonify(result)


@app.route('/favorites', methods=["GET"])
async def get_favorites():
    return jsonify({"favorites": list(favorites_cache.values())})


@app.route('/favorites/add', methods=["POST"])
async def post_favorites_add():
    data = await request.get_json(force=True, silent=True) or {}
    job_id = str(datetime.utcnow().timestamp())
    entity_job[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    # Fire and forget the processing task
    asyncio.create_task(process_add_favorite(job_id, data))
    return jsonify({"message": "Cat add request received", "job_id": job_id})


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```