from dataclasses import dataclass
from typing import Optional
import asyncio
import logging
from datetime import datetime
import random

import httpx
from quart import Blueprint, jsonify, request
from quart_schema import validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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

# Job function to fetch breeds and add minimal entities
async def fetch_breeds_job(job_id: str):
    breed_jobs[job_id]["status"] = "processing"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{CAT_API_BASE}/breeds")
            resp.raise_for_status()
            breeds = resp.json()
            for breed in breeds:
                minimal_breed = {
                    "id": breed.get("id"),
                    "name": breed.get("name"),
                }
                try:
                    await entity_service.add_item(
                        token=cyoda_auth_service,
                        entity_model="breed",
                        entity_version=ENTITY_VERSION,
                        entity=minimal_breed,
                    )
                except Exception as e:
                    logger.warning(f"Failed to add breed {minimal_breed.get('id')}: {e}")
        breed_jobs[job_id]["status"] = "completed"
        breed_jobs[job_id]["count"] = len(breeds)
    except Exception as e:
        logger.exception(e)
        breed_jobs[job_id]["status"] = "failed"

# Job function to fetch cat facts and add each as entity
async def fetch_facts_job(job_id: str, count: int):
    fact_jobs[job_id]["status"] = "processing"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            added_count = 0
            for _ in range(count):
                try:
                    r = await client.get(CAT_FACTS_API)
                    r.raise_for_status()
                    data = r.json()
                    fact_text = data.get("fact")
                    if fact_text:
                        await entity_service.add_item(
                            token=cyoda_auth_service,
                            entity_model="fact",
                            entity_version=ENTITY_VERSION,
                            entity={"fact": fact_text},
                        )
                        added_count += 1
                except Exception as e:
                    logger.warning(f"Failed fetching a cat fact: {e}")
        fact_jobs[job_id]["status"] = "completed"
        fact_jobs[job_id]["count"] = added_count
    except Exception as e:
        logger.exception(e)
        fact_jobs[job_id]["status"] = "failed"

# Job function to fetch images and add minimal image entities
async def fetch_images_job(job_id: str, breed: Optional[str], limit: int):
    image_jobs[job_id]["status"] = "processing"
    try:
        params = {"limit": limit}
        if breed:
            params["breed_id"] = breed
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{CAT_API_BASE}/images/search", params=params)
            resp.raise_for_status()
            data = resp.json()
            added_count = 0
            for item in data:
                url = item.get("url")
                if url:
                    try:
                        await entity_service.add_item(
                            token=cyoda_auth_service,
                            entity_model="image",
                            entity_version=ENTITY_VERSION,
                            entity={"url": url},
                        )
                        added_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to add image url {url}: {e}")
        image_jobs[job_id]["status"] = "completed"
        image_jobs[job_id]["count"] = added_count
    except Exception as e:
        logger.exception(e)
        image_jobs[job_id]["status"] = "failed"

@routes_bp.route("/breeds", methods=["GET"])
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

@routes_bp.route("/breeds/fetch", methods=["POST"])
@validate_request(FetchBreedsRequest)
async def fetch_breeds(data: FetchBreedsRequest):
    job_id = datetime.utcnow().isoformat()
    breed_jobs[job_id] = {"status": "queued", "requestedAt": job_id}
    asyncio.create_task(fetch_breeds_job(job_id))
    return jsonify({"status": "queued", "job_id": job_id})

@routes_bp.route("/facts/random", methods=["GET"])
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

@routes_bp.route("/facts/fetch", methods=["POST"])
@validate_request(FetchFactsRequest)
async def fetch_facts(data: FetchFactsRequest):
    count = data.count if data.count and data.count > 0 else 5
    job_id = datetime.utcnow().isoformat()
    fact_jobs[job_id] = {"status": "queued", "requestedAt": job_id}
    asyncio.create_task(fetch_facts_job(job_id, count=count))
    return jsonify({"status": "queued", "job_id": job_id})

@routes_bp.route("/images/random", methods=["GET"])
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

@routes_bp.route("/images/fetch", methods=["POST"])
@validate_request(FetchImagesRequest)
async def fetch_images(data: FetchImagesRequest):
    breed = data.breed
    limit = data.limit if data.limit and data.limit > 0 else 3
    job_id = datetime.utcnow().isoformat()
    image_jobs[job_id] = {"status": "queued", "requestedAt": job_id}
    asyncio.create_task(fetch_images_job(job_id, breed, limit))
    return jsonify({"status": "queued", "job_id": job_id})