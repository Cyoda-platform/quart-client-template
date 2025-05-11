from dataclasses import dataclass
from typing import Dict, List, Optional

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

cat_images: List[Dict] = []
cat_breeds: List[Dict] = []
cat_facts: List[str] = []
user_favorites: Dict[str, List[Dict]] = {}
entity_jobs: Dict[str, Dict] = {}

CAT_API_BASE = "https://api.thecatapi.com/v1"
CAT_FACTS_API = "https://catfact.ninja/fact"

@dataclass
class LiveDataRequest:
    dataType: str
    filters: Optional[dict] = None

@dataclass
class FavoriteRequest:
    userId: str
    favoriteType: str
    favoriteId: str

async def fetch_cat_images(limit: int = 10, breed: Optional[str] = None) -> List[Dict]:
    params = {"limit": limit}
    if breed:
        params["breed_ids"] = breed
    headers = {"x-api-key": ""}  # TODO: Add your TheCatAPI key here if you want higher rate limits
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{CAT_API_BASE}/images/search", params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data:
                breed_name = item["breeds"][0]["name"] if item.get("breeds") else None
                results.append({
                    "id": item["id"],
                    "url": item["url"],
                    "breed": breed_name,
                })
            return results
        except Exception as e:
            logger.exception(f"Failed to fetch cat images: {e}")
            return []

async def fetch_cat_breeds(limit: int = 10) -> List[Dict]:
    headers = {"x-api-key": ""}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{CAT_API_BASE}/breeds", headers=headers)
            resp.raise_for_status()
            data = resp.json()
            breeds = []
            for item in data[:limit]:
                breeds.append({
                    "id": item["id"],
                    "name": item["name"],
                    "origin": item.get("origin", ""),
                    "description": item.get("description", ""),
                })
            return breeds
        except Exception as e:
            logger.exception(f"Failed to fetch cat breeds: {e}")
            return []

async def fetch_cat_facts(limit: int = 5) -> List[str]:
    facts = []
    async with httpx.AsyncClient() as client:
        try:
            for _ in range(limit):
                resp = await client.get(CAT_FACTS_API)
                resp.raise_for_status()
                data = resp.json()
                fact = data.get("fact")
                if fact:
                    facts.append(fact)
            return facts
        except Exception as e:
            logger.exception(f"Failed to fetch cat facts: {e}")
            return []

async def process_live_data_job(job_id: str, data_type: str, filters: dict):
    try:
        logger.info(f"Started processing job {job_id} for dataType={data_type} filters={filters}")
        if data_type == "images":
            limit = filters.get("limit", 10) if filters else 10
            breed = filters.get("breed") if filters else None
            images = await fetch_cat_images(limit=limit, breed=breed)
            global cat_images
            cat_images = images
            count = len(images)

        elif data_type == "breeds":
            limit = filters.get("limit", 10) if filters else 10
            breeds = await fetch_cat_breeds(limit=limit)
            global cat_breeds
            cat_breeds = breeds
            count = len(breeds)

        elif data_type == "facts":
            limit = filters.get("limit", 5) if filters else 5
            facts = await fetch_cat_facts(limit=limit)
            global cat_facts
            cat_facts = facts
            count = len(facts)

        else:
            logger.warning(f"Unknown dataType requested: {data_type}")
            entity_jobs[job_id]["status"] = "failed"
            entity_jobs[job_id]["message"] = f"Unknown dataType: {data_type}"
            return

        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["count"] = count
        entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
        logger.info(f"Completed job {job_id} with {count} items for dataType={data_type}")

    except Exception as e:
        logger.exception(f"Error processing job {job_id}: {e}")
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["message"] = str(e)

@app.route("/cats/live-data", methods=["POST"])
@validate_request(LiveDataRequest)  # Validation last in POST (workaround issue)
async def post_live_data(data: LiveDataRequest):
    data_type = data.dataType
    filters = data.filters or {}

    job_id = f"job_{datetime.utcnow().timestamp()}"
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
        "dataType": data_type,
        "filters": filters,
    }

    asyncio.create_task(process_live_data_job(job_id, data_type, filters))

    return jsonify({
        "status": "success",
        "message": "Data fetch started",
        "jobId": job_id,
    })

@app.route("/cats/images", methods=["GET"])
async def get_cat_images():
    # No validation needed on GET with no params
    return jsonify({"images": cat_images})

@app.route("/cats/breeds", methods=["GET"])
async def get_cat_breeds():
    return jsonify({"breeds": cat_breeds})

@app.route("/cats/facts", methods=["GET"])
async def get_cat_facts():
    return jsonify({"facts": cat_facts})

@app.route("/cats/favorites", methods=["POST"])
@validate_request(FavoriteRequest)  # Validation last in POST (workaround issue)
async def post_favorites(data: FavoriteRequest):
    user_id = data.userId
    favorite_type = data.favoriteType
    favorite_id = data.favoriteId

    fav_list = user_favorites.setdefault(user_id, [])
    fav_list.append({
        "type": favorite_type,
        "id": favorite_id,
    })

    return jsonify({"status": "success", "message": "Favorite saved"})

@app.route("/cats/favorites", methods=["GET"])
async def get_favorites():
    # Workaround issue: validation must be first on GET but no query validation here,
    # so no @validate_querystring decorator used.
    user_id = request.args.get("userId")
    if not user_id:
        return jsonify({"status": "error", "message": "Missing userId query parameter"}), 400

    favs = user_favorites.get(user_id, [])
    enriched = []
    for fav in favs:
        if fav["type"] == "image":
            img = next((img for img in cat_images if img["id"] == fav["id"]), None)
            if img:
                enriched.append({
                    "type": "image",
                    "id": img["id"],
                    "url": img["url"],
                    "breed": img.get("breed")
                })
            else:
                enriched.append(fav)
        elif fav["type"] == "breed":
            breed = next((b for b in cat_breeds if b["id"] == fav["id"]), None)
            if breed:
                enriched.append({
                    "type": "breed",
                    "id": breed["id"],
                    "name": breed["name"],
                    "origin": breed.get("origin"),
                    "description": breed.get("description"),
                })
            else:
                enriched.append(fav)
        else:
            enriched.append(fav)

    return jsonify({"favorites": enriched})

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
