```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Union

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache to store fetched data
# Structure:
# {
#   "images": [{id, url}],
#   "facts": [{id, text}],
#   "breeds": [{id, name, origin, description}]
# }
data_store: Dict[str, List[Dict]] = {
    "images": [],
    "facts": [],
    "breeds": []
}

# Simulated job tracking for fetch requests
entity_jobs: Dict[str, Dict] = {}

# Real external APIs chosen:
# - Cat facts: https://catfact.ninja/fact (single random fact)
# - Cat images: https://api.thecatapi.com/v1/images/search
# - Cat breeds: https://api.thecatapi.com/v1/breeds

CAT_API_BASE = "https://api.thecatapi.com/v1"
CAT_FACT_API = "https://catfact.ninja/fact"

# TODO: For thecatapi.com, you can optionally add an API key header if needed.
# For prototype, it's optional and free tier allows some calls.


async def fetch_cat_images(count: int) -> List[Dict]:
    url = f"{CAT_API_BASE}/images/search?limit={count}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            images = resp.json()
            result = []
            for img in images:
                result.append({"id": img.get("id"), "url": img.get("url")})
            return result
        except Exception as e:
            logger.exception(f"Failed to fetch cat images: {e}")
            return []


async def fetch_cat_facts(count: int) -> List[Dict]:
    results = []
    async with httpx.AsyncClient() as client:
        try:
            for _ in range(count):
                resp = await client.get(CAT_FACT_API)
                resp.raise_for_status()
                fact_json = resp.json()
                # fact_json example: {"fact": "...", "length": 50}
                results.append({"id": f"fact_{datetime.utcnow().timestamp()}", "text": fact_json.get("fact")})
            return results
        except Exception as e:
            logger.exception(f"Failed to fetch cat facts: {e}")
            return []


async def fetch_cat_breeds(count: int) -> List[Dict]:
    url = f"{CAT_API_BASE}/breeds"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            breeds = resp.json()
            selected = breeds[:count]
            result = []
            for b in selected:
                result.append({
                    "id": b.get("id"),
                    "name": b.get("name"),
                    "origin": b.get("origin"),
                    "description": b.get("description")
                })
            return result
        except Exception as e:
            logger.exception(f"Failed to fetch cat breeds: {e}")
            return []


async def process_entity(job_id: str, data_type: str, count: int):
    logger.info(f"Started processing job {job_id} for type {data_type} count {count}")
    try:
        if data_type == "images":
            fetched = await fetch_cat_images(count)
            data_store["images"].extend(fetched)
        elif data_type == "facts":
            fetched = await fetch_cat_facts(count)
            data_store["facts"].extend(fetched)
        elif data_type == "breeds":
            fetched = await fetch_cat_breeds(count)
            data_store["breeds"].extend(fetched)
        else:
            logger.warning(f"Unknown data type requested: {data_type}")
            entity_jobs[job_id]["status"] = "failed"
            return

        entity_jobs[job_id]["status"] = "completed"
        logger.info(f"Completed job {job_id} successfully")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        logger.exception(f"Error processing job {job_id}: {e}")


@app.route("/cats/fetch", methods=["POST"])
async def cats_fetch():
    """
    Request JSON example:
    {
      "type": "images" | "facts" | "breeds",
      "count": 1
    }
    """
    try:
        data = await request.get_json()
        data_type = data.get("type")
        count = data.get("count", 1)

        if data_type not in ("images", "facts", "breeds"):
            return jsonify({"status": "error", "message": "Invalid type parameter"}), 400
        if not isinstance(count, int) or count < 1:
            return jsonify({"status": "error", "message": "Count must be a positive integer"}), 400

        job_id = f"job_{datetime.utcnow().timestamp()}"
        entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}

        # Fire and forget the processing task
        asyncio.create_task(process_entity(job_id, data_type, count))

        return jsonify({
            "status": "success",
            "message": f"Cat data fetch started for {data_type}",
            "job_id": job_id
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@app.route("/cats/images", methods=["GET"])
async def cats_images():
    return jsonify({"images": data_store["images"]})


@app.route("/cats/facts", methods=["GET"])
async def cats_facts():
    return jsonify({"facts": data_store["facts"]})


@app.route("/cats/breeds", methods=["GET"])
async def cats_breeds():
    return jsonify({"breeds": data_store["breeds"]})


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
