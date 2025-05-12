```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for prototype persistence
# Structure example: 
# {
#   "images": [{id: str, content: str}, ...],
#   "breeds": [{id: str, content: dict}, ...],
#   "facts": [{id: str, content: str}, ...]
# }
data_store: Dict[str, List[Dict[str, Any]]] = {
    "images": [],
    "breeds": [],
    "facts": []
}

# Track jobs for demonstration
entity_job: Dict[str, Dict[str, Any]] = {}

# External APIs used:
# - TheCatAPI (https://docs.thecatapi.com/) for images and breeds
# - Cat Facts API (https://catfact.ninja/) for facts

THE_CAT_API_BASE = "https://api.thecatapi.com/v1"
CAT_FACTS_API_BASE = "https://catfact.ninja"

# TODO: Add your TheCatAPI API key here if needed; for prototype, it works without one.
THE_CAT_API_HEADERS = {
    # "x-api-key": "YOUR_API_KEY"
}

# Helper to generate simple unique IDs for stored data items
def generate_id(prefix: str, idx: int) -> str:
    return f"{prefix}_{idx}"

async def fetch_cat_images(limit: int = 5) -> List[Dict[str, Any]]:
    url = f"{THE_CAT_API_BASE}/images/search?limit={limit}"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=THE_CAT_API_HEADERS, timeout=10)
            resp.raise_for_status()
            items = resp.json()
            return [{"id": generate_id("img", i), "content": item["url"]} for i, item in enumerate(items)]
    except Exception as e:
        logger.exception(f"Failed to fetch cat images: {e}")
        return []

async def fetch_cat_breeds(limit: int = 10) -> List[Dict[str, Any]]:
    url = f"{THE_CAT_API_BASE}/breeds"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=THE_CAT_API_HEADERS, timeout=10)
            resp.raise_for_status()
            items = resp.json()
            # Limit breeds if requested
            breeds = items[:limit]
            return [{"id": breed["id"], "content": breed} for breed in breeds]
    except Exception as e:
        logger.exception(f"Failed to fetch cat breeds: {e}")
        return []

async def fetch_cat_facts(limit: int = 5) -> List[Dict[str, Any]]:
    url = f"{CAT_FACTS_API_BASE}/facts?limit={limit}"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            facts = data.get("data", [])
            return [{"id": generate_id("fact", i), "content": fact["fact"]} for i, fact in enumerate(facts)]
    except Exception as e:
        logger.exception(f"Failed to fetch cat facts: {e}")
        return []

async def process_fetch_data(job_id: str, params: Dict[str, Any]):
    try:
        source = params.get("source", "default")  # only 'default' supported in prototype
        data_types = params.get("dataTypes", [])
        filters = params.get("filters", {})
        limit = filters.get("limit", 5)

        # Clear data_store for requested types to simulate fresh fetch
        for dt in data_types:
            data_store[dt] = []

        # Fetch data for requested types
        if "images" in data_types:
            imgs = await fetch_cat_images(limit=limit)
            data_store["images"].extend(imgs)

        if "breeds" in data_types:
            breeds_limit = limit if limit else 10
            breeds = await fetch_cat_breeds(limit=breeds_limit)
            # Apply breed filter if present
            breed_filter = filters.get("breed")
            if breed_filter:
                breeds = [b for b in breeds if breed_filter.lower() in b["content"]["name"].lower()]
            data_store["breeds"].extend(breeds)

        if "facts" in data_types:
            facts = await fetch_cat_facts(limit=limit)
            data_store["facts"].extend(facts)

        entity_job[job_id]["status"] = "completed"
        entity_job[job_id]["completedAt"] = datetime.utcnow().isoformat()
        entity_job[job_id]["count"] = sum(len(data_store.get(dt, [])) for dt in data_types)

        logger.info(f"Job {job_id} completed, fetched data types: {data_types}")

    except Exception as e:
        entity_job[job_id]["status"] = "failed"
        logger.exception(f"Failed processing fetch data job {job_id}: {e}")

@app.route("/cats/data/fetch", methods=["POST"])
async def cats_data_fetch():
    data: Dict[str, Any] = await request.get_json(force=True)
    job_id = f"job_{datetime.utcnow().timestamp()}"
    requested_at = datetime.utcnow().isoformat()
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}
    # Fire and forget the processing task
    asyncio.create_task(process_fetch_data(job_id, data))
    return jsonify({"status": "processing", "jobId": job_id, "requestedAt": requested_at}), 202

@app.route("/cats/data", methods=["GET"])
async def cats_data_get():
    data_type = request.args.get("type", None)
    breed_filter = request.args.get("breed", None)
    limit = request.args.get("limit", None)
    try:
        limit = int(limit) if limit else None
    except ValueError:
        limit = None

    if data_type not in data_store:
        return jsonify({"error": f"Unsupported data type '{data_type}'"}), 400

    data_items = data_store.get(data_type, [])

    # Apply breed filter for breeds data_type only
    if data_type == "breeds" and breed_filter:
        data_items = [item for item in data_items if breed_filter.lower() in item["content"]["name"].lower()]

    if limit:
        data_items = data_items[:limit]

    return jsonify({"dataType": data_type, "data": data_items})

@app.route("/cats/data/analyze", methods=["POST"])
async def cats_data_analyze():
    data: Dict[str, Any] = await request.get_json(force=True)
    analysis_type = data.get("analysisType")
    parameters = data.get("parameters", {})

    # Example analysis implementations:

    if analysis_type == "popularity":
        # TODO: For prototype, mock popularity as count of stored breeds
        breed_name = parameters.get("breed")
        if breed_name:
            # Count how many images or facts mention the breed name (mock)
            count_images = sum(1 for i in data_store["images"] if breed_name.lower() in i["content"].lower())
            count_facts = sum(1 for f in data_store["facts"] if breed_name.lower() in f["content"].lower())
            result = {"breed": breed_name, "popularityScore": count_images + count_facts}
        else:
            result = {"error": "breed parameter required for popularity analysis"}
        return jsonify({"analysisType": analysis_type, "result": result})

    elif analysis_type == "factFrequency":
        # Count frequency of words in facts (simple example)
        word_count: Dict[str, int] = {}
        for fact_item in data_store["facts"]:
            words = fact_item["content"].lower().split()
            for w in words:
                word_count[w] = word_count.get(w, 0) + 1
        # Return top 10 words for prototype
        top_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:10]
        result = {word: count for word, count in top_words}
        return jsonify({"analysisType": analysis_type, "result": result})

    else:
        return jsonify({"error": f"Unsupported analysis type '{analysis_type}'"}), 400


if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
