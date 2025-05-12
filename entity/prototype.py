```python
import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory caches to mock persistence
entity_job = {}  # job_id -> {status, requestedAt, result}
user_favorites = {}  # userId -> set(catId)
cat_data_store = {}  # catId -> cat info (breed, imageUrl, fact)

# External API info
CAT_API_BASE = "https://api.thecatapi.com/v1"
CAT_API_KEY = None  # TODO: optionally set your key for higher rate limits


async def fetch_cat_breeds():
    headers = {}
    if CAT_API_KEY:
        headers["x-api-key"] = CAT_API_KEY
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{CAT_API_BASE}/breeds", headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()


async def fetch_cat_image(breed_id: str):
    headers = {}
    if CAT_API_KEY:
        headers["x-api-key"] = CAT_API_KEY
    params = {"breed_ids": breed_id, "limit": 1}
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{CAT_API_BASE}/images/search", headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        imgs = resp.json()
        if imgs:
            return imgs[0].get("url")
    return None


async def fetch_cat_fact():
    # Using https://catfact.ninja/fact
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://catfact.ninja/fact", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("fact")


async def process_entity(job_id, filters):
    try:
        logger.info(f"Started processing job {job_id} with filters: {filters}")
        breeds = await fetch_cat_breeds()

        # Filter breeds if breed filter is provided (case insensitive substring match)
        filtered_breeds = breeds
        breed_filter = filters.get("breed")
        if breed_filter:
            filtered_breeds = [
                b for b in breeds if breed_filter.lower() in b.get("name", "").lower()
            ]

        results = []
        # Limit the number of cats returned to max 10 to avoid overload
        max_cats = 10
        for breed in filtered_breeds[:max_cats]:
            breed_id = breed.get("id")
            breed_name = breed.get("name")
            image_url = await fetch_cat_image(breed_id)
            fact = await fetch_cat_fact()

            cat_id = str(uuid.uuid4())
            cat_info = {
                "id": cat_id,
                "breed": breed_name,
                "imageUrl": image_url or "",
                "fact": fact or "",
            }
            cat_data_store[cat_id] = cat_info
            results.append(cat_info)

        entity_job[job_id]["status"] = "completed"
        entity_job[job_id]["result"] = results
        logger.info(f"Completed processing job {job_id} with {len(results)} cats")
    except Exception as e:
        logger.exception(e)
        entity_job[job_id]["status"] = "failed"
        entity_job[job_id]["result"] = {"error": str(e)}


@app.route("/cats/data", methods=["POST"])
async def post_cats_data():
    data = await request.get_json(force=True)
    filters = data.get("filters", {}) if isinstance(data, dict) else {}
    job_id = str(uuid.uuid4())
    entity_job[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}
    # Fire and forget processing task
    asyncio.create_task(process_entity(job_id, filters))
    return jsonify({"status": "success", "processedDataId": job_id})


@app.route("/cats/data/<processed_data_id>", methods=["GET"])
async def get_cats_data(processed_data_id):
    job = entity_job.get(processed_data_id)
    if not job:
        return jsonify({"error": "Processed data ID not found"}), 404

    if job["status"] == "processing":
        return jsonify({"status": "processing"}), 202

    if job["status"] == "failed":
        return jsonify({"status": "failed", "error": job["result"].get("error")}), 500

    return jsonify({
        "processedDataId": processed_data_id,
        "cats": job.get("result", [])
    })


@app.route("/cats/favorites", methods=["POST"])
async def post_cats_favorites():
    data = await request.get_json(force=True)
    user_id = data.get("userId")
    cat_id = data.get("catId")

    if not user_id or not cat_id:
        return jsonify({"error": "userId and catId are required"}), 400

    # Check catId exists in cat_data_store
    if cat_id not in cat_data_store:
        return jsonify({"error": "catId not found"}), 404

    favorites = user_favorites.setdefault(user_id, set())
    favorites.add(cat_id)
    return jsonify({"status": "success"})


@app.route("/cats/favorites/<user_id>", methods=["GET"])
async def get_cats_favorites(user_id):
    favorites = user_favorites.get(user_id, set())
    cats = [cat_data_store[cat_id] for cat_id in favorites if cat_id in cat_data_store]

    return jsonify({
        "userId": user_id,
        "favorites": cats
    })


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
