from dataclasses import dataclass
from typing import Optional, List, Dict, Any

import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache for prototype persistence
data_store: Dict[str, List[Dict[str, Any]]] = {
    "images": [],
    "breeds": [],
    "facts": []
}

entity_job: Dict[str, Dict[str, Any]] = {}

THE_CAT_API_BASE = "https://api.thecatapi.com/v1"
CAT_FACTS_API_BASE = "https://catfact.ninja"
THE_CAT_API_HEADERS = {
    # "x-api-key": "YOUR_API_KEY"  # TODO: Add API key if needed
}

def generate_id(prefix: str, idx: int) -> str:
    return f"{prefix}_{idx}"

@dataclass
class FetchDataRequest:
    source: Optional[str] = "default"
    dataTypes: List[str] = None
    filters: Optional[Dict[str, Any]] = None

@dataclass
class AnalyzeDataRequest:
    analysisType: str
    parameters: Optional[Dict[str, Any]] = None

@dataclass
class CatsDataGetQuery:
    type: Optional[str] = None
    breed: Optional[str] = None
    limit: Optional[int] = None

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

async def process_fetch_data(job_id: str, params: FetchDataRequest):
    try:
        source = params.source or "default"
        data_types = params.dataTypes or []
        filters = params.filters or {}
        limit = filters.get("limit", 5)

        for dt in data_types:
            data_store[dt] = []

        if "images" in data_types:
            imgs = await fetch_cat_images(limit=limit)
            data_store["images"].extend(imgs)

        if "breeds" in data_types:
            breeds_limit = limit if limit else 10
            breeds = await fetch_cat_breeds(limit=breeds_limit)
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
@validate_request(FetchDataRequest)  # POST validation last (issue workaround)
async def cats_data_fetch(data: FetchDataRequest):
    job_id = f"job_{datetime.utcnow().timestamp()}"
    requested_at = datetime.utcnow().isoformat()
    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}
    asyncio.create_task(process_fetch_data(job_id, data))
    return jsonify({"status": "processing", "jobId": job_id, "requestedAt": requested_at}), 202

# GET validation first (issue workaround)
@app.route("/cats/data", methods=["GET"])
@validate_querystring(CatsDataGetQuery)
async def cats_data_get():
    query_args = request.args
    data_type = query_args.get("type", None)
    breed_filter = query_args.get("breed", None)
    limit = query_args.get("limit", None)
    try:
        limit = int(limit) if limit else None
    except ValueError:
        limit = None

    if data_type not in data_store:
        return jsonify({"error": f"Unsupported data type '{data_type}'"}), 400

    data_items = data_store.get(data_type, [])

    if data_type == "breeds" and breed_filter:
        data_items = [item for item in data_items if breed_filter.lower() in item["content"]["name"].lower()]

    if limit:
        data_items = data_items[:limit]

    return jsonify({"dataType": data_type, "data": data_items})

@app.route("/cats/data/analyze", methods=["POST"])
@validate_request(AnalyzeDataRequest)  # POST validation last (issue workaround)
async def cats_data_analyze(data: AnalyzeDataRequest):
    analysis_type = data.analysisType
    parameters = data.parameters or {}

    if analysis_type == "popularity":
        breed_name = parameters.get("breed")
        if breed_name:
            count_images = sum(1 for i in data_store["images"] if breed_name.lower() in i["content"].lower())
            count_facts = sum(1 for f in data_store["facts"] if breed_name.lower() in f["content"].lower())
            result = {"breed": breed_name, "popularityScore": count_images + count_facts}
        else:
            result = {"error": "breed parameter required for popularity analysis"}
        return jsonify({"analysisType": analysis_type, "result": result})

    elif analysis_type == "factFrequency":
        word_count = {}
        for fact_item in data_store["facts"]:
            words = fact_item["content"].lower().split()
            for w in words:
                word_count[w] = word_count.get(w, 0) + 1
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