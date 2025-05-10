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

# In-memory local cache to mock persistence
cat_breeds_cache: Dict[str, Dict] = {}
entity_jobs: Dict[str, Dict] = {}

THE_CAT_API_BREEDS_URL = "https://api.thecatapi.com/v1/breeds"
THE_CAT_API_IMAGES_URL = "https://api.thecatapi.com/v1/images/search"


async def fetch_breed_image(client: httpx.AsyncClient, breed_id: str) -> Optional[str]:
    """
    Fetch a representative image URL for a given breed from The Cat API.
    """
    try:
        params = {"breed_id": breed_id, "limit": 1}
        resp = await client.get(THE_CAT_API_IMAGES_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data and isinstance(data, list) and "url" in data[0]:
            return data[0]["url"]
    except Exception as e:
        logger.exception(f"Failed to fetch image for breed {breed_id}: {e}")
    return None


async def process_fetch_breeds_job(job_id: str):
    """
    Background task to fetch breeds data + images and store in local cache.
    """
    logger.info(f"Start processing job {job_id} to fetch breeds data")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(THE_CAT_API_BREEDS_URL)
            resp.raise_for_status()
            breeds = resp.json()
            # Clear cache before update
            cat_breeds_cache.clear()

            # For each breed, fetch a single image URL
            tasks = []
            for breed in breeds:
                breed_id = breed.get("id")
                if not breed_id:
                    continue
                tasks.append(fetch_breed_image(client, breed_id))

            images = await asyncio.gather(*tasks)

            for breed, image_url in zip(breeds, images):
                breed_id = breed["id"]
                cat_breeds_cache[breed_id] = {
                    "id": breed_id,
                    "name": breed.get("name", ""),
                    "description": breed.get("description", ""),
                    "image_url": image_url or "",
                }
        entity_jobs[job_id]["status"] = "completed"
        logger.info(f"Job {job_id} completed successfully")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        logger.exception(f"Job {job_id} failed: {e}")


@app.route("/api/cats/fetch-breeds", methods=["POST"])
async def fetch_breeds():
    """
    POST endpoint to fetch breeds data from The Cat API and store it internally.
    Returns immediately with job id; processing is async.
    """
    job_id = datetime.utcnow().isoformat() + "-job"
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}

    # Fire and forget the processing task
    asyncio.create_task(process_fetch_breeds_job(job_id))

    return jsonify({"status": "processing", "job_id": job_id})


@app.route("/api/cats/breeds", methods=["GET"])
async def get_all_breeds():
    """
    GET endpoint to return all stored cat breeds with images.
    """
    breeds_list = list(cat_breeds_cache.values())
    return jsonify(breeds_list)


@app.route("/api/cats/breeds/<breed_id>", methods=["GET"])
async def get_breed_by_id(breed_id: str):
    """
    GET endpoint to return specific breed info by breed ID.
    """
    breed = cat_breeds_cache.get(breed_id)
    if not breed:
        return jsonify({"error": "Breed not found"}), 404
    return jsonify(breed)


@app.route("/api/cats/jobs/<job_id>", methods=["GET"])
async def get_job_status(job_id: str):
    """
    Optional: endpoint to check status of fetch-breeds job.
    """
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
