from dataclasses import dataclass, field
from typing import Optional, Dict, Any

import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)


@dataclass
class CatDataRequest:
    type: str
    filters: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class RandomCatRequest:
    includeImage: Optional[bool] = True


# In-memory cache for storing last fetched data
cached_cat_data = {
    "facts": [],
    "images": [],
    "breeds": [],
    "last_updated": None
}

# Entity job store simulation for processing jobs
entity_job = {}

# External APIs
CAT_FACTS_API = "https://catfact.ninja/facts"
CAT_BREEDS_API = "https://api.thecatapi.com/v1/breeds"
CAT_IMAGES_API = "https://api.thecatapi.com/v1/images/search"

# Optional: You can set your CAT_API_KEY here if you have one (some endpoints may require it)
CAT_API_KEY = None

headers = {}
if CAT_API_KEY:
    headers["x-api-key"] = CAT_API_KEY


async def fetch_cat_facts(limit: int = 10, breed: Optional[str] = None, age: Optional[str] = None):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(CAT_FACTS_API, params={"limit": limit})
            resp.raise_for_status()
            data = resp.json()
            return [fact["fact"] for fact in data.get("data", [])]
    except Exception as e:
        logger.exception(e)
        return []


async def fetch_cat_breeds(limit: int = 10, breed_filter: Optional[str] = None):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(CAT_BREEDS_API, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            breeds = data
            if breed_filter:
                breeds = [b for b in breeds if breed_filter.lower() in b["name"].lower()]
            return breeds[:limit]
    except Exception as e:
        logger.exception(e)
        return []


async def fetch_cat_images(limit: int = 10, breed_filter: Optional[str] = None):
    try:
        async with httpx.AsyncClient() as client:
            params = {"limit": limit}
            if breed_filter:
                # TODO: implement breed name to id mapping for filtering images
                pass
            resp = await client.get(CAT_IMAGES_API, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            return [img["url"] for img in data]
    except Exception as e:
        logger.exception(e)
        return []


async def process_cat_data(request_id: str, data_type: str, filters: dict):
    try:
        limit = filters.get("limit", 10)
        breed = filters.get("breed")
        age = filters.get("age")  # Not used currently - no API supports age filtering

        if data_type == "facts":
            results = await fetch_cat_facts(limit, breed, age)
            cached_cat_data["facts"] = results
        elif data_type == "breeds":
            results = await fetch_cat_breeds(limit, breed)
            cached_cat_data["breeds"] = results
        elif data_type == "images":
            results = await fetch_cat_images(limit, breed)
            cached_cat_data["images"] = results
        else:
            results = []

        cached_cat_data["last_updated"] = datetime.utcnow().isoformat()

        entity_job[request_id]["status"] = "completed"
        entity_job[request_id]["result"] = results

        logger.info(f"Processed job {request_id} for data type '{data_type}'")
    except Exception as e:
        entity_job[request_id]["status"] = "failed"
        entity_job[request_id]["error"] = str(e)
        logger.exception(e)


@app.route("/cats/data", methods=["POST"])
@validate_request(CatDataRequest)  # Validation last in POST - known quart-schema issue workaround
async def post_cats_data(data: CatDataRequest):
    data_type = data.type
    filters = data.filters or {}

    if data_type not in {"facts", "images", "breeds"}:
        return jsonify({"status": "error", "message": "Invalid type specified"}), 400

    request_id = datetime.utcnow().isoformat() + "_" + data_type
    entity_job[request_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}

    # Fire and forget processing task
    asyncio.create_task(process_cat_data(request_id, data_type, filters))

    return jsonify({"status": "processing", "job_id": request_id})


# No request parameters to validate for GET /cats/results, so no validation decorator here
@app.route("/cats/results", methods=["GET"])
async def get_cats_results():
    # Returns cached cat data for all types
    return jsonify({
        "status": "success",
        "data": {
            "facts": cached_cat_data.get("facts", []),
            "images": cached_cat_data.get("images", []),
            "breeds": cached_cat_data.get("breeds", []),
            "last_updated": cached_cat_data.get("last_updated")
        }
    })


# Validation first in POST - known quart-schema issue workaround
@app.route("/cats/random", methods=["POST"])
@validate_request(RandomCatRequest)
async def post_cats_random(data: RandomCatRequest):
    include_image = data.includeImage if data.includeImage is not None else True

    try:
        # Fetch one random fact
        facts = await fetch_cat_facts(1)
        fact = facts[0] if facts else "Cats are mysterious creatures."

        image_url = None
        if include_image:
            images = await fetch_cat_images(1)
            image_url = images[0] if images else None

        result = {"fact": fact}
        if image_url:
            result["image"] = image_url

        return jsonify({"status": "success", "cat": result})

    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": "Failed to fetch random cat"}), 500


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
