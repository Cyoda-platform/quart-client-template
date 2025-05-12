from dataclasses import dataclass
from typing import Optional, Literal, List
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request
import httpx
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

cached_cats: List[dict] = []
favorite_cats: set = set()
entity_jobs = {}

CAT_API_BASE = "https://api.thecatapi.com/v1"
CAT_FACTS_API = "https://catfact.ninja/fact"

@dataclass
class CatsDataRequest:
    type: Literal["random", "breed"]
    breed_name: Optional[str] = None

@dataclass
class FavoriteCatRequest:
    cat_id: str

# Helper async function to fetch cat images & breeds from TheCatAPI
async def fetch_cat_images(breed_name: Optional[str] = None) -> List[dict]:
    async with httpx.AsyncClient() as client:
        params = {}
        if breed_name:
            resp = await client.get(f"{CAT_API_BASE}/breeds/search", params={"q": breed_name})
            resp.raise_for_status()
            breeds = resp.json()
            if not breeds:
                logger.info(f"No breeds found for: {breed_name}")
                return []
            breed_id = breeds[0]["id"]
            params["breed_ids"] = breed_id

        resp = await client.get(f"{CAT_API_BASE}/images/search", params={**params, "limit": 5})
        resp.raise_for_status()
        images = resp.json()
        cats = []
        for img in images:
            cat_breeds = img.get("breeds", [])
            cat_breed = cat_breeds[0]["name"] if cat_breeds else (breed_name or "Unknown")
            cats.append({
                "id": img.get("id"),
                "breed": cat_breed,
                "image_url": img.get("url"),
                "fact": None
            })
        return cats

async def fetch_cat_facts(count: int) -> List[str]:
    facts = []
    async with httpx.AsyncClient() as client:
        for _ in range(count):
            try:
                resp = await client.get(CAT_FACTS_API)
                resp.raise_for_status()
                data = resp.json()
                fact = data.get("fact")
                if fact:
                    facts.append(fact)
            except Exception as e:
                logger.exception(e)
                facts.append("Cats are mysterious creatures.")
    return facts

async def process_entity(job_id: str, data: CatsDataRequest):
    try:
        logger.info(f"Processing job {job_id} with data {data}")

        if data.type == "random":
            cats = await fetch_cat_images()
        elif data.type == "breed" and data.breed_name:
            cats = await fetch_cat_images(data.breed_name)
        else:
            cats = []
            logger.info("Invalid type or missing breed_name in request data")

        if not cats:
            logger.info("No cat images found, returning empty list")

        facts = await fetch_cat_facts(len(cats))

        for i, cat in enumerate(cats):
            cat["fact"] = facts[i] if i < len(facts) else "Cats are wonderful."

        global cached_cats
        cached_cats = cats

        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["result"] = cats
        logger.info(f"Job {job_id} completed successfully")

    except Exception as e:
        logger.exception(e)
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["result"] = []

# POST routes must have @app.route first, then @validate_request (workaround issue in quart-schema)
@app.route("/cats/data", methods=["POST"])
@validate_request(CatsDataRequest)
async def post_cats_data(data: CatsDataRequest):
    job_id = datetime.utcnow().isoformat() + "-" + str(id(data))
    entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    asyncio.create_task(process_entity(job_id, data))
    return jsonify({"job_id": job_id, "status": "processing"}), 202

# GET routes must have @validate_request first, then @app.route (workaround issue in quart-schema)
# However, GET /cats has no request parameters so no validation needed here
@app.route("/cats", methods=["GET"])
async def get_cats():
    if not cached_cats:
        return jsonify({"cats": [], "message": "No cat data available. Trigger POST /cats/data to fetch."}), 200
    return jsonify({"cats": cached_cats}), 200

@app.route("/cats/favorite", methods=["POST"])
@validate_request(FavoriteCatRequest)
async def post_favorite_cat(data: FavoriteCatRequest):
    cat_id = data.cat_id
    if not any(cat["id"] == cat_id for cat in cached_cats):
        return jsonify({"status": "failure", "message": "Invalid 'cat_id', not found in cached cats"}), 404

    favorite_cats.add(cat_id)
    return jsonify({"status": "success", "message": f"Cat {cat_id} added to favorites."}), 200

if __name__ == "__main__":
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
