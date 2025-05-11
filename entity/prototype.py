```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory local cache to mock persistence
entity_job: Dict[str, Dict[str, Any]] = {}
last_results_cache: Dict[str, Any] = {"data": []}

# Real external APIs for cat data:
# - Cat Facts: https://catfact.ninja/fact
# - Cat Breeds: https://api.thecatapi.com/v1/breeds
# - Cat Images: https://api.thecatapi.com/v1/images/search

CAT_FACT_API = "https://catfact.ninja/fact"
CAT_BREEDS_API = "https://api.thecatapi.com/v1/breeds"
CAT_IMAGES_API = "https://api.thecatapi.com/v1/images/search"

# TheCatAPI requires an API key for high usage, but allows some free requests without it.
# TODO: Add API key if needed, for now we proceed without one.


async def fetch_cat_fact(client: httpx.AsyncClient) -> Dict[str, Any]:
    resp = await client.get(CAT_FACT_API)
    resp.raise_for_status()
    data = resp.json()
    return {"fact": data.get("fact")}


async def fetch_cat_breeds(client: httpx.AsyncClient, limit: int = 10, breed_filter: str = None) -> Any:
    resp = await client.get(CAT_BREEDS_API)
    resp.raise_for_status()
    breeds = resp.json()
    if breed_filter:
        breeds = [b for b in breeds if breed_filter.lower() in b.get("name", "").lower()]
    return breeds[:limit]


async def fetch_cat_images(client: httpx.AsyncClient, limit: int = 1) -> Any:
    params = {"limit": limit}
    resp = await client.get(CAT_IMAGES_API, params=params)
    resp.raise_for_status()
    return resp.json()


async def process_entity(job: Dict[str, Any], data: Dict[str, Any]):
    try:
        job["status"] = "processing"
        job["startedAt"] = datetime.utcnow().isoformat()
        async with httpx.AsyncClient(timeout=10) as client:
            cat_type = data.get("type")
            filters = data.get("filters", {})
            limit = filters.get("limit", 10)
            breed = filters.get("breed")

            if cat_type == "facts":
                results = []
                # Fetch multiple facts by calling API multiple times (not ideal but this API returns one per call)
                for _ in range(limit):
                    fact = await fetch_cat_fact(client)
                    results.append(fact)
            elif cat_type == "breeds":
                results = await fetch_cat_breeds(client, limit=limit, breed_filter=breed)
            elif cat_type == "images":
                results = await fetch_cat_images(client, limit=limit)
            else:
                results = []
                logger.warning(f"Unknown type requested: {cat_type}")

            # Cache last results globally (for demo, no user separation)
            last_results_cache["data"] = results
            job["status"] = "completed"
            job["completedAt"] = datetime.utcnow().isoformat()
            job["resultCount"] = len(results)
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        logger.exception(e)


@app.route("/api/cats/data", methods=["POST"])
async def post_cat_data():
    data = await request.get_json(force=True)
    job_id = datetime.utcnow().isoformat()
    entity_job[job_id] = {"status": "queued", "requestedAt": job_id}

    # Fire and forget processing
    asyncio.create_task(process_entity(entity_job[job_id], data))

    return jsonify({"status": "accepted", "job_id": job_id}), 202


@app.route("/api/cats/results", methods=["GET"])
async def get_cat_results():
    # Return last cached results
    # TODO: Enhance to accept job_id or user_id for scoped results
    return jsonify({"status": "success", "data": last_results_cache["data"]})


@app.route("/api/cats/submit-photo", methods=["POST"])
async def post_cat_photo():
    data = await request.get_json(force=True)
    # Mock storing photo submission
    logger.info(f"Received photo submission: user_id={data.get('user_id')}, photo_url={data.get('photo_url')}")
    # TODO: Persist photo submissions in real storage
    return jsonify({"status": "success", "message": "Photo submitted"})


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
