```python
import asyncio
import logging
from datetime import datetime
from typing import Dict

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory "persistence" stores
cat_facts_store: Dict[str, Dict] = {}
cat_images_store: Dict[str, Dict] = {}
cat_breeds_store: Dict[str, Dict] = {}

# Simple ID generators
def generate_id(prefix: str, store: Dict) -> str:
    return f"{prefix}{len(store) + 1}"

# External APIs
CAT_FACT_API = "https://catfact.ninja/fact"
CAT_IMAGE_API = "https://api.thecatapi.com/v1/images/search"
CAT_BREEDS_API = "https://api.thecatapi.com/v1/breeds"

# Jobs to track async processing
entity_jobs = {}

async def fetch_cat_fact() -> Dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(CAT_FACT_API)
        resp.raise_for_status()
        data = resp.json()
        return {"fact": data.get("fact", "No fact returned")}

async def fetch_cat_image() -> Dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(CAT_IMAGE_API)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            return {"url": data[0].get("url", "")}
        return {"url": ""}

async def fetch_cat_breeds() -> Dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(CAT_BREEDS_API)
        resp.raise_for_status()
        data = resp.json()
        # Extract only id and name as per spec
        breeds = [{"id": b.get("id"), "name": b.get("name")} for b in data]
        return {"breeds": breeds}

async def process_cat_fact(job_id: str):
    try:
        fact_data = await fetch_cat_fact()
        fact_id = generate_id("fact", cat_facts_store)
        cat_facts_store[fact_id] = {"id": fact_id, "fact": fact_data["fact"]}
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = cat_facts_store[fact_id]
        logger.info(f"Cat fact stored with id: {fact_id}")
    except Exception as e:
        logger.exception(e)
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)

async def process_cat_image(job_id: str):
    try:
        image_data = await fetch_cat_image()
        image_id = generate_id("image", cat_images_store)
        cat_images_store[image_id] = {"id": image_id, "url": image_data["url"]}
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = cat_images_store[image_id]
        logger.info(f"Cat image stored with id: {image_id}")
    except Exception as e:
        logger.exception(e)
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)

async def process_cat_breeds(job_id: str):
    try:
        breeds_data = await fetch_cat_breeds()
        # Replace entire store on each fetch
        cat_breeds_store.clear()
        for b in breeds_data["breeds"]:
            cat_breeds_store[b["id"]] = b
        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = {"breeds": list(cat_breeds_store.values())}
        logger.info(f"Cat breeds list updated with {len(cat_breeds_store)} breeds")
    except Exception as e:
        logger.exception(e)
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)

# POST /cats/facts/random
@app.route("/cats/facts/random", methods=["POST"])
async def post_random_cat_fact():
    job_id = generate_id("job", entity_jobs)
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    asyncio.create_task(process_cat_fact(job_id))
    return jsonify({"job_id": job_id, "status": "processing"}), 202

# GET /cats/facts/{id}
@app.route("/cats/facts/<fact_id>", methods=["GET"])
async def get_cat_fact(fact_id: str):
    fact = cat_facts_store.get(fact_id)
    if not fact:
        return jsonify({"error": "Fact not found"}), 404
    return jsonify(fact)

# POST /cats/images/random
@app.route("/cats/images/random", methods=["POST"])
async def post_random_cat_image():
    job_id = generate_id("job", entity_jobs)
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    asyncio.create_task(process_cat_image(job_id))
    return jsonify({"job_id": job_id, "status": "processing"}), 202

# GET /cats/images/{id}
@app.route("/cats/images/<image_id>", methods=["GET"])
async def get_cat_image(image_id: str):
    image = cat_images_store.get(image_id)
    if not image:
        return jsonify({"error": "Image not found"}), 404
    return jsonify(image)

# POST /cats/breeds/list
@app.route("/cats/breeds/list", methods=["POST"])
async def post_cat_breeds_list():
    job_id = generate_id("job", entity_jobs)
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    asyncio.create_task(process_cat_breeds(job_id))
    return jsonify({"job_id": job_id, "status": "processing"}), 202

# GET /cats/breeds
@app.route("/cats/breeds", methods=["GET"])
async def get_cat_breeds():
    if not cat_breeds_store:
        return jsonify({"error": "No breeds data available. Please POST /cats/breeds/list first."}), 404
    return jsonify({"breeds": list(cat_breeds_store.values())})

# Optional: GET job status (not in spec but useful for prototype)
@app.route("/jobs/<job_id>", methods=["GET"])
async def get_job_status(job_id: str):
    job = entity_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
