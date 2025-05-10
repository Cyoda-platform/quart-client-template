```python
import asyncio
import logging
from datetime import datetime
from typing import Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory storage mocks
cat_facts = []
cat_images = []
cat_breeds = []

# Track entity jobs
entity_jobs = {}

# External APIs (real)
CAT_FACTS_API = "https://catfact.ninja/fact"
CAT_BREEDS_API = "https://api.thecatapi.com/v1/breeds"
CAT_IMAGES_API = "https://api.thecatapi.com/v1/images/search"


async def fetch_cat_fact(client: httpx.AsyncClient) -> Optional[str]:
    try:
        r = await client.get(CAT_FACTS_API)
        r.raise_for_status()
        data = r.json()
        return data.get("fact")
    except Exception as e:
        logger.exception(f"Failed to fetch cat fact: {e}")
        return None


async def fetch_cat_breeds(client: httpx.AsyncClient) -> list:
    try:
        r = await client.get(CAT_BREEDS_API)
        r.raise_for_status()
        data = r.json()
        # Extract relevant info
        breeds = []
        for breed in data:
            breeds.append({
                "name": breed.get("name"),
                "origin": breed.get("origin"),
                "description": breed.get("description")
            })
        return breeds
    except Exception as e:
        logger.exception(f"Failed to fetch cat breeds: {e}")
        return []


async def fetch_cat_images(client: httpx.AsyncClient, limit: int = 5) -> list:
    try:
        params = {"limit": limit}
        r = await client.get(CAT_IMAGES_API, params=params)
        r.raise_for_status()
        data = r.json()
        # Extract URLs
        images = [item.get("url") for item in data if item.get("url")]
        return images
    except Exception as e:
        logger.exception(f"Failed to fetch cat images: {e}")
        return []


async def process_entity(job_id: str, source: str, data_type: str):
    """Background task to fetch and update data."""
    logger.info(f"Started processing job {job_id} for source={source}, dataType={data_type}")
    async with httpx.AsyncClient(timeout=10) as client:
        count = 0

        if data_type in ("facts", "all"):
            fact = await fetch_cat_fact(client)
            if fact:
                cat_facts.append(fact)
                count += 1

        if data_type in ("breeds", "all"):
            breeds = await fetch_cat_breeds(client)
            if breeds:
                cat_breeds.clear()
                cat_breeds.extend(breeds)
                count += len(breeds)

        if data_type in ("images", "all"):
            images = await fetch_cat_images(client, limit=5)
            if images:
                cat_images.clear()
                cat_images.extend(images)
                count += len(images)

    entity_jobs[job_id]["status"] = "completed"
    entity_jobs[job_id]["fetchedDataCount"] = count
    entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
    logger.info(f"Completed processing job {job_id}, fetched {count} items.")


@app.route("/cats/data", methods=["POST"])
async def update_cat_data():
    req = await request.get_json(force=True)
    source = req.get("source", "all")  # currently unused, could be extended
    data_type = req.get("dataType", "all")

    job_id = datetime.utcnow().isoformat() + "_job"
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "fetchedDataCount": 0,
        "completedAt": None,
    }

    # Fire and forget background task
    asyncio.create_task(process_entity(job_id, source, data_type))

    return jsonify({
        "status": "success",
        "message": f"Data update triggered for dataType={data_type}",
        "jobId": job_id,
    })


@app.route("/cats/facts", methods=["GET"])
async def get_cat_facts():
    return jsonify({"facts": cat_facts})


@app.route("/cats/images", methods=["GET"])
async def get_cat_images():
    return jsonify({"images": cat_images})


@app.route("/cats/breeds", methods=["GET"])
async def get_cat_breeds():
    return jsonify({"breeds": cat_breeds})


if __name__ == '__main__':
    import sys
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
        stream=sys.stdout,
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
