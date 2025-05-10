from dataclasses import dataclass
from typing import Optional
import asyncio
import logging
from datetime import datetime
import random

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Local in-memory caches for prototype persistence
breeds_cache = []
facts_cache = []
images_cache = []

breed_jobs = {}
fact_jobs = {}
image_jobs = {}

CAT_API_BASE = "https://api.thecatapi.com/v1"
CAT_FACTS_API = "https://catfact.ninja/fact"

@dataclass
class FetchBreedsRequest:
    # No fields for now, placeholder
    pass

@dataclass
class FetchFactsRequest:
    count: Optional[int] = 5

@dataclass
class FetchImagesRequest:
    breed: Optional[str] = None
    limit: Optional[int] = 3


async def fetch_breeds_from_external():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{CAT_API_BASE}/breeds")
            response.raise_for_status()
            breeds = response.json()
            simplified = [
                {
                    "id": b.get("id"),
                    "name": b.get("name"),
                    "origin": b.get("origin"),
                    "description": b.get("description"),
                }
                for b in breeds
            ]
            return simplified
        except Exception as e:
            logger.exception(e)
            return None

async def fetch_cat_facts_external(count: int = 5):
    facts = []
    async with httpx.AsyncClient() as client:
        for _ in range(count):
            try:
                r = await client.get(CAT_FACTS_API)
                r.raise_for_status()
                data = r.json()
                fact = data.get("fact")
                if fact:
                    facts.append(fact)
            except Exception as e:
                logger.exception(e)
    return facts

async def fetch_cat_images_external(breed_id: Optional[str], limit: int):
    params = {"limit": limit}
    if breed_id:
        params["breed_id"] = breed_id
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{CAT_API_BASE}/images/search", params=params)
            resp.raise_for_status()
            data = resp.json()
            urls = [item.get("url") for item in data if item.get("url")]
            return urls
        except Exception as e:
            logger.exception(e)
            return []

async def process_breeds_job(job_id: str):
    breed_jobs[job_id]["status"] = "processing"
    try:
        breeds = await fetch_breeds_from_external()
        if breeds is not None:
            global breeds_cache
            breeds_cache = breeds
            breed_jobs[job_id]["status"] = "completed"
            breed_jobs[job_id]["count"] = len(breeds)
        else:
            breed_jobs[job_id]["status"] = "failed"
    except Exception as e:
        logger.exception(e)
        breed_jobs[job_id]["status"] = "failed"

async def process_facts_job(job_id: str, count: int):
    fact_jobs[job_id]["status"] = "processing"
    try:
        facts = await fetch_cat_facts_external(count)
        if facts:
            global facts_cache
            for f in facts:
                if f not in facts_cache:
                    facts_cache.append(f)
            fact_jobs[job_id]["status"] = "completed"
            fact_jobs[job_id]["count"] = len(facts)
        else:
            fact_jobs[job_id]["status"] = "failed"
    except Exception as e:
        logger.exception(e)
        fact_jobs[job_id]["status"] = "failed"

async def process_images_job(job_id: str, breed: Optional[str], limit: int):
    image_jobs[job_id]["status"] = "processing"
    try:
        images = await fetch_cat_images_external(breed, limit)
        if images:
            global images_cache
            for img in images:
                if img not in images_cache:
                    images_cache.append(img)
            image_jobs[job_id]["status"] = "completed"
            image_jobs[job_id]["count"] = len(images)
        else:
            image_jobs[job_id]["status"] = "failed"
    except Exception as e:
        logger.exception(e)
        image_jobs[job_id]["status"] = "failed"


@app.route("/breeds", methods=["GET"])
# Workaround: validate first for GET requests due to quart-schema issue
async def get_breeds():
    return jsonify(breeds_cache)


@app.route("/breeds/fetch", methods=["POST"])
@validate_request(FetchBreedsRequest)  # Workaround: validate last for POST requests due to quart-schema issue
async def fetch_breeds(data: FetchBreedsRequest):
    job_id = datetime.utcnow().isoformat()
    breed_jobs[job_id] = {"status": "queued", "requestedAt": job_id}
    asyncio.create_task(process_breeds_job(job_id))
    return jsonify({"status": "queued", "job_id": job_id})


@app.route("/facts/random", methods=["GET"])
async def get_random_fact():
    if not facts_cache:
        return jsonify({"fact": "No facts available. Please POST to /facts/fetch first."}), 404
    fact = random.choice(facts_cache)
    return jsonify({"fact": fact})


@app.route("/facts/fetch", methods=["POST"])
@validate_request(FetchFactsRequest)  # Workaround: validate last for POST requests due to quart-schema issue
async def fetch_facts(data: FetchFactsRequest):
    count = data.count if data.count and data.count > 0 else 5
    job_id = datetime.utcnow().isoformat()
    fact_jobs[job_id] = {"status": "queued", "requestedAt": job_id}
    asyncio.create_task(process_facts_job(job_id, count=count))
    return jsonify({"status": "queued", "job_id": job_id})


@app.route("/images/random", methods=["GET"])
async def get_random_image():
    if not images_cache:
        return jsonify({"url": None, "message": "No images available. Please POST to /images/fetch first."}), 404
    url = random.choice(images_cache)
    return jsonify({"url": url})


@app.route("/images/fetch", methods=["POST"])
@validate_request(FetchImagesRequest)  # Workaround: validate last for POST requests due to quart-schema issue
async def fetch_images(data: FetchImagesRequest):
    breed = data.breed
    limit = data.limit if data.limit and data.limit > 0 else 3
    job_id = datetime.utcnow().isoformat()
    image_jobs[job_id] = {"status": "queued", "requestedAt": job_id}
    asyncio.create_task(process_images_job(job_id, breed, limit))
    return jsonify({"status": "queued", "job_id": job_id})


if __name__ == "__main__":
    import sys

    if sys.platform == "win32":
        import asyncio

        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
