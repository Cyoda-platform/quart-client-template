Got it! To follow the requirements and best practices, I will move as much logic as possible into the workflow functions `process_breed`, `process_fact`, and `process_image`.

**Key points:**

- The workflow function replaces asynchronous "pre-persistence" logic related to that entity.
- These functions receive the entity dict as the only argument.
- They can mutate the entity to update its state before persistence.
- They can fetch or add supplementary entities of *different* entity_models, but **cannot** add/update/delete the same entity_model (to avoid recursion).
- Fire-and-forget async tasks related to entity enrichment or data fetching fit well here.

---

### Changes I will make:

**1. Breeds:**

- Current fetching breeds from external API and adding is done in a separate async task `process_breeds_job`.
- We cannot add the same entity_model inside the workflow function for a breed entity (would cause recursion).
- But we can move the external API fetch logic into the workflow function that is called for an initial placeholder breed entity (say with minimal info).
- However, the current pattern is to fetch *all* breeds externally and add them one by one. We cannot do that inside a single workflow function since it applies to a single entity.
- So for breeds, probably the best we can do is keep the initial fetch in the job, but if we want to enrich or mutate the breed entity before saving, that logic moves inside `process_breed`.

**2. Facts:**

- The current fetching of facts is done by `process_facts_job`, which fetches facts externally and adds them one by one.
- Again, since adding the same entity_model inside the workflow causes infinite recursion, we cannot fetch multiple facts inside `process_fact`.
- However, if a fact entity is created with minimal info, `process_fact` can enrich the fact entity (e.g. add timestamp, source, or transform the fact text).
- If we want to fire-and-forget fetch multiple facts, we must keep it outside or implement a separate job.

**3. Images:**

- Similar to facts.
- If an image entity is created with minimal info, `process_image` can enrich the image entity (e.g. add metadata).
- But we cannot add images inside the image workflow function.

---

### To satisfy the requirement:

- Move all enrichment and transformation logic inside `process_{entity_name}` workflow functions.
- Keep the external fetching of multiple entities or batches in the respective job functions.
- The job functions will create minimal entities, and the workflow will enrich them before persistence.
- Remove any duplicated async logic from endpoints.

---

### Updated code:

```python
from dataclasses import dataclass
from typing import Optional
import asyncio
import logging
from datetime import datetime
import random

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

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


async def process_breed(entity: dict) -> dict:
    """
    Workflow function for breed entity.
    Enrich breed with additional data from external API if needed.
    This function is called before the breed entity is persisted.
    """

    # If entity has minimal info (e.g., just id), fetch full details from external API
    if "description" not in entity or not entity.get("description"):
        breed_id = entity.get("id")
        if breed_id:
            async with httpx.AsyncClient() as client:
                try:
                    resp = await client.get(f"{CAT_API_BASE}/breeds/{breed_id}")
                    resp.raise_for_status()
                    data = resp.json()
                    # Update entity with enriched data fields
                    entity["name"] = data.get("name", entity.get("name"))
                    entity["origin"] = data.get("origin", entity.get("origin"))
                    entity["description"] = data.get("description", "")
                except Exception as e:
                    logger.warning(f"Failed to enrich breed {breed_id}: {e}")

    # Add timestamp for when the breed was processed
    entity["processed_at"] = datetime.utcnow().isoformat()

    # Example: Add supplementary entities (different entity_model) here if needed
    # e.g., add a 'fact' entity related to this breed (without updating this breed)
    # await entity_service.add_item(
    #     token=cyoda_auth_service,
    #     entity_model="fact",
    #     entity_version=ENTITY_VERSION,
    #     entity={"fact": f"Interesting fact about {entity.get('name', 'this breed')}."},
    #     workflow=process_fact,
    # )

    return entity


async def process_fact(entity: dict) -> dict:
    """
    Workflow function for fact entity.
    Enrich or modify facts before persistence.
    """

    # Add timestamps
    entity.setdefault("created_at", datetime.utcnow().isoformat())

    # Normalize fact text - example: capitalize first letter
    fact_text = entity.get("fact", "")
    if fact_text:
        entity["fact"] = fact_text[0].upper() + fact_text[1:]

    # Optionally, fetch related breed or image info as supplementary entities
    # For example, if fact mentions a breed, add that breed entity asynchronously (fire and forget)
    # But only if we have such info in fact (not in this example)

    return entity


async def process_image(entity: dict) -> dict:
    """
    Workflow function for image entity.
    Enrich image entity before persistence.
    """

    # Add processed timestamp
    entity["processed_at"] = datetime.utcnow().isoformat()

    # Optionally fetch metadata about image (e.g., size, format) asynchronously
    url = entity.get("url")
    if url:
        try:
            async with httpx.AsyncClient() as client:
                head_resp = await client.head(url)
                if head_resp.status_code == 200:
                    entity["content_type"] = head_resp.headers.get("Content-Type", "")
                    entity["content_length"] = int(head_resp.headers.get("Content-Length", "0"))
        except Exception as e:
            logger.warning(f"Failed to fetch metadata for image: {e}")

    return entity


async def fetch_breeds_job(job_id: str):
    breed_jobs[job_id]["status"] = "processing"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{CAT_API_BASE}/breeds")
            resp.raise_for_status()
            breeds = resp.json()
            for breed in breeds:
                # Add minimal breed entity; enrichment happens in workflow
                minimal_breed = {
                    "id": breed.get("id"),
                    "name": breed.get("name"),
                    # do NOT add description here, let workflow fetch it on demand
                }
                try:
                    await entity_service.add_item(
                        token=cyoda_auth_service,
                        entity_model="breed",
                        entity_version=ENTITY_VERSION,
                        entity=minimal_breed,
                        workflow=process_breed,
                    )
                except Exception as e:
                    logger.warning(f"Failed to add breed {minimal_breed.get('id')}: {e}")
        breed_jobs[job_id]["status"] = "completed"
        breed_jobs[job_id]["count"] = len(breeds)
    except Exception as e:
        logger.exception(e)
        breed_jobs[job_id]["status"] = "failed"


async def fetch_facts_job(job_id: str, count: int):
    fact_jobs[job_id]["status"] = "processing"
    try:
        async with httpx.AsyncClient() as client:
            for _ in range(count):
                try:
                    r = await client.get(CAT_FACTS_API)
                    r.raise_for_status()
                    data = r.json()
                    fact_text = data.get("fact")
                    if fact_text:
                        # Add fact entity, enrichment such as timestamp and normalization in workflow
                        await entity_service.add_item(
                            token=cyoda_auth_service,
                            entity_model="fact",
                            entity_version=ENTITY_VERSION,
                            entity={"fact": fact_text},
                            workflow=process_fact,
                        )
                except Exception as e:
                    logger.warning(f"Failed fetching a cat fact: {e}")
        fact_jobs[job_id]["status"] = "completed"
        fact_jobs[job_id]["count"] = count
    except Exception as e:
        logger.exception(e)
        fact_jobs[job_id]["status"] = "failed"


async def fetch_images_job(job_id: str, breed: Optional[str], limit: int):
    image_jobs[job_id]["status"] = "processing"
    try:
        params = {"limit": limit}
        if breed:
            params["breed_id"] = breed
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{CAT_API_BASE}/images/search", params=params)
            resp.raise_for_status()
            data = resp.json()
            for item in data:
                url = item.get("url")
                if url:
                    # Add minimal image entity; enrichment in workflow (content-type, length)
                    try:
                        await entity_service.add_item(
                            token=cyoda_auth_service,
                            entity_model="image",
                            entity_version=ENTITY_VERSION,
                            entity={"url": url},
                            workflow=process_image,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to add image url {url}: {e}")
        image_jobs[job_id]["status"] = "completed"
        image_jobs[job_id]["count"] = len(data)
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
    asyncio.create_task(fetch_breeds_job(job_id))
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
    asyncio.create_task(fetch_facts_job(job_id, count=count))
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
    asyncio.create_task(fetch_images_job(job_id, breed, limit))
    return jsonify({"status": "queued", "job_id": job_id})


if __name__ == "__main__":
    import sys

    if sys.platform == "win32":
        import asyncio

        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```

---

## Explanation

- All "enrichment" or "pre-persistence transformation" logic moved into respective `process_{entity_name}` functions.
- The job functions only fetch raw data and create minimal entities.
- The workflow functions enrich entities (e.g. fetch missing data, normalize text, add timestamps, fetch image metadata).
- Endpoints only trigger job functions or retrieve entities — no business logic inside the endpoints.
- This approach complies with the requirement to move async pre-persistence logic into workflow functions and keeps endpoint controllers clean and minimal.

---

Let me know if you want me to further optimize, e.g. move job creation logic inside workflows too or handle more complex scenarios!