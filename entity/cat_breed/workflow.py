import asyncio
import logging
from datetime import datetime
from typing import Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request
from dataclasses import dataclass

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

CAT_FACTS_API = "https://catfact.ninja/fact"
CAT_BREEDS_API = "https://api.thecatapi.com/v1/breeds"
CAT_IMAGES_API = "https://api.thecatapi.com/v1/images/search"

cat_facts = []
cat_images = []
cat_breeds = []

entity_jobs = {}

@dataclass
class CatDataRequest:
    source: Optional[str] = "all"
    dataType: Optional[str] = "all"

async def process_fetch_fact(entity: dict):
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(CAT_FACTS_API)
            r.raise_for_status()
            data = r.json()
            fact = data.get("fact")
            if fact:
                cat_facts.append(fact)
                entity['fetched_count'] = entity.get('fetched_count', 0) + 1
        except Exception as e:
            logger.exception(f"Failed to fetch cat fact: {e}")

async def process_fetch_breeds(entity: dict):
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(CAT_BREEDS_API)
            r.raise_for_status()
            data = r.json()
            breeds = []
            for breed in data:
                breeds.append({
                    "name": breed.get("name"),
                    "origin": breed.get("origin"),
                    "description": breed.get("description")
                })
            if breeds:
                cat_breeds.clear()
                cat_breeds.extend(breeds)
                entity['fetched_count'] = entity.get('fetched_count', 0) + len(breeds)
        except Exception as e:
            logger.exception(f"Failed to fetch cat breeds: {e}")

async def process_fetch_images(entity: dict):
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            params = {"limit": 5}
            r = await client.get(CAT_IMAGES_API, params=params)
            r.raise_for_status()
            data = r.json()
            images = [item.get("url") for item in data if item.get("url")]
            if images:
                cat_images.clear()
                cat_images.extend(images)
                entity['fetched_count'] = entity.get('fetched_count', 0) + len(images)
        except Exception as e:
            logger.exception(f"Failed to fetch cat images: {e}")

@app.route("/cats/data", methods=["POST"])
@validate_request(CatDataRequest)  # Validation last in POST method (issue workaround)
async def update_cat_data(data: CatDataRequest):
    job_id = datetime.utcnow().isoformat() + "_job"
    entity = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "fetched_count": 0,
        "completedAt": None,
        "source": data.source or "all",
        "dataType": data.dataType or "all",
        "jobId": job_id
    }
    entity_jobs[job_id] = entity

    asyncio.create_task(process_cat_breed(entity))

    return jsonify({
        "status": "success",
        "message": f"Data update triggered for dataType={entity['dataType']}",
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