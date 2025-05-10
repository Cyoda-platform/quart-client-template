from dataclasses import dataclass
from typing import Optional
import asyncio
import logging
from datetime import datetime
import random

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

import logging
from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

CAT_API_BASE = "https://api.thecatapi.com/v1"
CAT_FACTS_API = "https://catfact.ninja/fact"

@dataclass
class FetchBreedsRequest:
    pass

@dataclass
class FetchFactsRequest:
    count: Optional[int] = 5

@dataclass
class FetchImagesRequest:
    breed: Optional[str] = None
    limit: Optional[int] = 3

breed_jobs = {}
fact_jobs = {}
image_jobs = {}

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
            for breed in breeds:
                try:
                    await entity_service.add_item(
                        token=cyoda_auth_service,
                        entity_model="breed",
                        entity_version=ENTITY_VERSION,
                        entity=breed,
                    )
                except Exception as e:
                    logger.exception(e)
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
            for fact in facts:
                try:
                    await entity_service.add_item(
                        token=cyoda_auth_service,
                        entity_model="fact",
                        entity_version=ENTITY_VERSION,
                        entity={"fact": fact},
                    )
                except Exception as e:
                    logger.exception(e)
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
            for url in images:
                try:
                    await entity_service.add_item(
                        token=cyoda_auth_service,
                        entity_model="image",
                        entity_version=ENTITY_VERSION,
                        entity={"url": url},
                    )
                except Exception as e:
                    logger.exception(e)
            image_jobs[job_id]["status"] = "completed"
            image_jobs[job_id]["count"] = len(images)
        else:
            image_jobs[job_id]["status"] = "failed"
    except Exception as e:
        logger.exception(e)
        image_jobs[job_id]["status"] = "failed"


@app.route("/breeds", methods=["GET"])
async def get_breeds():
    try:
        breeds = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="breed",
            entity_version=ENTITY_VERSION,
        )
        return jsonify(breeds)
    except Exception as e:
        logger.exception(e)
        return jsonify([]), 500

@app.route("/breeds/fetch", methods=["POST"])
@validate_request(FetchBreedsRequest)
async def fetch_breeds(data: FetchBreedsRequest):
    job_id = datetime.utcnow().isoformat()
    breed_jobs[job_id] = {"status": "queued", "requestedAt": job_id}
    asyncio.create_task(process_breeds_job(job_id))
    return jsonify({"status": "queued", "job_id": job_id})

@app.route("/facts/random", methods=["GET"])
async def get_random_fact():
    try:
        facts = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="fact",
            entity_version=ENTITY_VERSION,
        )
        if not facts:
            return jsonify({"fact": "No facts available. Please POST to /facts/fetch first."}), 404
        fact = random.choice(facts)
        return jsonify({"fact": fact.get("fact")})
    except Exception as e:
        logger.exception(e)
        return jsonify({"fact": "Error retrieving facts."}), 500

@app.route("/facts/fetch", methods=["POST"])
@validate_request(FetchFactsRequest)
async def fetch_facts(data: FetchFactsRequest):
    count = data.count if data.count and data.count > 0 else 5
    job_id = datetime.utcnow().isoformat()
    fact_jobs[job_id] = {"status": "queued", "requestedAt": job_id}
    asyncio.create_task(process_facts_job(job_id, count=count))
    return jsonify({"status": "queued", "job_id": job_id})

@app.route("/images/random", methods=["GET"])
async def get_random_image():
    try:
        images = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="image",
            entity_version=ENTITY_VERSION,
        )
        if not images:
            return jsonify({"url": None, "message": "No images available. Please POST to /images/fetch first."}), 404
        url = random.choice(images).get("url")
        return jsonify({"url": url})
    except Exception as e:
        logger.exception(e)
        return jsonify({"url": None, "message": "Error retrieving images."}), 500

@app.route("/images/fetch", methods=["POST"])
@validate_request(FetchImagesRequest)
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