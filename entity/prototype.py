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

# In-memory caches for GET endpoints to return last fetched results
cache = {
    "random_cats": None,   # type: Optional[List[Dict]]
    "breeds_info": None,   # type: Optional[List[Dict]]
    "cat_facts": None      # type: Optional[List[str]]
}

# Job status tracking for fire-and-forget pattern
entity_job = {}

# External APIs
CAT_API_BASE = "https://api.thecatapi.com/v1"
CAT_FACTS_API = "https://catfact.ninja/facts"


async def fetch_random_cats(count: int) -> List[Dict]:
    """
    Fetch random cat images and breed info from TheCatAPI.
    """
    logger.info(f"Fetching {count} random cats from external API")
    async with httpx.AsyncClient() as client:
        try:
            # TheCatAPI random images with breed info included
            params = {"limit": count, "size": "med", "order": "Random"}
            resp = await client.get(f"{CAT_API_BASE}/images/search", params=params)
            resp.raise_for_status()
            data = resp.json()

            cats = []
            for item in data:
                breed = item.get("breeds")[0] if item.get("breeds") else {}
                cats.append({
                    "id": item.get("id"),
                    "image_url": item.get("url"),
                    "breed": breed.get("name", "Unknown"),
                    "description": breed.get("description", ""),
                })
            return cats

        except Exception as e:
            logger.exception(f"Error fetching random cats: {e}")
            return []


async def fetch_breeds_info(breeds: List[str]) -> List[Dict]:
    """
    Fetch info for given breed names from TheCatAPI.
    """
    logger.info(f"Fetching breeds info for: {breeds}")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{CAT_API_BASE}/breeds")
            resp.raise_for_status()
            all_breeds = resp.json()

            result = []
            breed_set = set(b.lower() for b in breeds)
            for breed in all_breeds:
                if breed["name"].lower() in breed_set:
                    result.append({
                        "name": breed.get("name"),
                        "origin": breed.get("origin"),
                        "temperament": breed.get("temperament"),
                        "description": breed.get("description"),
                    })
            return result

        except Exception as e:
            logger.exception(f"Error fetching breeds info: {e}")
            return []


async def fetch_cat_facts(count: int) -> List[str]:
    """
    Fetch cat facts from catfact.ninja API.
    """
    logger.info(f"Fetching {count} cat facts")
    async with httpx.AsyncClient() as client:
        try:
            facts = []
            # catfact.ninja API supports only 1 fact per request; batch count requests
            for _ in range(count):
                resp = await client.get(CAT_FACTS_API, params={"limit": 1})
                resp.raise_for_status()
                data = resp.json()
                if data.get("data") and len(data["data"]) > 0:
                    facts.append(data["data"][0].get("fact"))
            return facts

        except Exception as e:
            logger.exception(f"Error fetching cat facts: {e}")
            return []


async def process_random_cats(job_id: str, count: int):
    try:
        cats = await fetch_random_cats(count)
        cache["random_cats"] = cats
        entity_job[job_id]["status"] = "completed"
        entity_job[job_id]["result"] = cats
        entity_job[job_id]["completedAt"] = datetime.utcnow().isoformat()
        logger.info(f"Completed job {job_id} with {len(cats)} cats")
    except Exception as e:
        logger.exception(e)
        entity_job[job_id]["status"] = "failed"


async def process_breeds_info(job_id: str, breeds: List[str]):
    try:
        breeds_info = await fetch_breeds_info(breeds)
        cache["breeds_info"] = breeds_info
        entity_job[job_id]["status"] = "completed"
        entity_job[job_id]["result"] = breeds_info
        entity_job[job_id]["completedAt"] = datetime.utcnow().isoformat()
        logger.info(f"Completed job {job_id} with {len(breeds_info)} breeds info")
    except Exception as e:
        logger.exception(e)
        entity_job[job_id]["status"] = "failed"


async def process_cat_facts(job_id: str, count: int):
    try:
        facts = await fetch_cat_facts(count)
        cache["cat_facts"] = facts
        entity_job[job_id]["status"] = "completed"
        entity_job[job_id]["result"] = facts
        entity_job[job_id]["completedAt"] = datetime.utcnow().isoformat()
        logger.info(f"Completed job {job_id} with {len(facts)} facts")
    except Exception as e:
        logger.exception(e)
        entity_job[job_id]["status"] = "failed"


@app.route("/cats/random", methods=["POST"])
async def cats_random_post():
    data = await request.get_json()
    count = data.get("count", 1)
    job_id = f"random_cats_{datetime.utcnow().timestamp()}"

    entity_job[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
    }
    asyncio.create_task(process_random_cats(job_id, count))
    return jsonify({"job_id": job_id, "status": "processing"}), 202


@app.route("/cats/random", methods=["GET"])
async def cats_random_get():
    if cache["random_cats"]:
        return jsonify({"cats": cache["random_cats"]})
    return jsonify({"cats": []}), 204


@app.route("/cats/breeds", methods=["POST"])
async def cats_breeds_post():
    data = await request.get_json()
    breeds = data.get("breeds", [])
    if not isinstance(breeds, list) or not breeds:
        return jsonify({"error": "Field 'breeds' must be a non-empty list"}), 400

    job_id = f"breeds_info_{datetime.utcnow().timestamp()}"
    entity_job[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
    }
    asyncio.create_task(process_breeds_info(job_id, breeds))
    return jsonify({"job_id": job_id, "status": "processing"}), 202


@app.route("/cats/breeds", methods=["GET"])
async def cats_breeds_get():
    if cache["breeds_info"]:
        return jsonify({"breeds_info": cache["breeds_info"]})
    return jsonify({"breeds_info": []}), 204


@app.route("/cats/facts", methods=["POST"])
async def cats_facts_post():
    data = await request.get_json()
    count = data.get("count", 1)
    job_id = f"cat_facts_{datetime.utcnow().timestamp()}"
    entity_job[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
    }
    asyncio.create_task(process_cat_facts(job_id, count))
    return jsonify({"job_id": job_id, "status": "processing"}), 202


@app.route("/cats/facts", methods=["GET"])
async def cats_facts_get():
    if cache["cat_facts"]:
        return jsonify({"facts": cache["cat_facts"]})
    return jsonify({"facts": []}), 204


@app.route("/jobs/<job_id>", methods=["GET"])
async def job_status(job_id):
    job = entity_job.get(job_id)
    if not job:
        return jsonify({"error": "Job ID not found"}), 404
    return jsonify(job)


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
