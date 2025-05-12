from dataclasses import dataclass
from typing import Dict, Optional

import asyncio
import logging
from datetime import datetime
from typing import List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory caches/mocks
latest_cat_data: List[Dict] = []
favorite_cats: List[Dict] = []
entity_job: Dict[str, Dict] = {}  # job_id -> job info/status


# External API base URLs for real live cat data
CAT_FACTS_API = "https://catfact.ninja/facts"
CAT_BREEDS_API = "https://api.thecatapi.com/v1/breeds"
CAT_IMAGES_API = "https://api.thecatapi.com/v1/images/search"

# TODO: Get an API key for https://thecatapi.com if needed (optional, public endpoints available)


async def fetch_cat_facts(filters: Optional[Dict]) -> List[Dict]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(CAT_FACTS_API)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
    except Exception as e:
        logger.exception(e)
        return []


async def fetch_cat_breeds(filters: Optional[Dict]) -> List[Dict]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(CAT_BREEDS_API)
            response.raise_for_status()
            breeds = response.json()
            if filters and "breed" in filters:
                filtered = [
                    b for b in breeds
                    if filters["breed"].lower() in b.get("name", "").lower()
                ]
                return filtered
            else:
                return breeds
    except Exception as e:
        logger.exception(e)
        return []


async def fetch_cat_images(filters: Optional[Dict]) -> List[Dict]:
    try:
        params = {"limit": 5}
        if filters and "breed" in filters:
            breeds = await fetch_cat_breeds({"breed": filters["breed"]})
            if breeds:
                breed_id = breeds[0].get("id")
                if breed_id:
                    params["breed_id"] = breed_id

        async with httpx.AsyncClient() as client:
            response = await client.get(CAT_IMAGES_API, params=params)
            response.raise_for_status()
            images = response.json()
            return images
    except Exception as e:
        logger.exception(e)
        return []


async def process_entity(job_id: str, data_type: str, filters: Optional[Dict]):
    try:
        entity_job[job_id]["status"] = "processing"
        if data_type == "facts":
            data = await fetch_cat_facts(filters)
        elif data_type == "breeds":
            data = await fetch_cat_breeds(filters)
        elif data_type == "images":
            data = await fetch_cat_images(filters)
        elif data_type == "random":
            facts = await fetch_cat_facts(filters)
            images = await fetch_cat_images(filters)
            breeds = await fetch_cat_breeds(filters)
            data = {
                "facts": facts[:3],
                "images": images[:3],
                "breeds": breeds[:3],
            }
        else:
            data = []

        global latest_cat_data
        latest_cat_data = data if isinstance(data, list) else [data]

        entity_job[job_id]["status"] = "done"
        entity_job[job_id]["result"] = latest_cat_data
        entity_job[job_id]["completedAt"] = datetime.utcnow().isoformat()
    except Exception as e:
        logger.exception(e)
        entity_job[job_id]["status"] = "error"
        entity_job[job_id]["error"] = str(e)


@dataclass
class LiveDataRequest:
    data_type: str
    filters: Optional[Dict] = None


@dataclass
class FavoriteRequest:
    cat_id: str
    user_id: Optional[str] = None


# POST /cats/live-data
@app.route("/cats/live-data", methods=["POST"])
@validate_request(LiveDataRequest)  # validation last for POST - issue workaround
async def post_live_data(data: LiveDataRequest):
    try:
        job_id = datetime.utcnow().isoformat()
        entity_job[job_id] = {"status": "queued", "requestedAt": job_id}
        asyncio.create_task(process_entity(job_id, data.data_type, data.filters))
        return jsonify({"status": "processing", "job_id": job_id})
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500


# GET /cats/latest - no validation needed (no parameters)
@app.route("/cats/latest", methods=["GET"])
async def get_latest():
    try:
        return jsonify({"status": "success", "data": latest_cat_data})
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500


# POST /cats/favorites
@app.route("/cats/favorites", methods=["POST"])
@validate_request(FavoriteRequest)  # validation last for POST - issue workaround
async def post_favorite(data: FavoriteRequest):
    try:
        if not data.cat_id:
            return jsonify({"status": "error", "message": "Missing cat_id"}), 400

        favorite_cats.append({
            "cat_id": data.cat_id,
            "user_id": data.user_id,
            "added_at": datetime.utcnow().isoformat()
        })
        return jsonify({"status": "success", "message": "Cat added to favorites"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500


# GET /cats/favorites - no validation needed (no parameters)
@app.route("/cats/favorites", methods=["GET"])
async def get_favorites():
    try:
        return jsonify({"status": "success", "data": favorite_cats})
    except Exception as e:
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
