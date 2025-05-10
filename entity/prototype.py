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

# In-memory cache to mock persistence
# Structure: { "facts": [...], "images": [...], "breeds": [...] }
cached_cat_data: Dict[str, List] = {
    "facts": [],
    "images": [],
    "breeds": []
}

# In-memory storage for favorites
favorites: List[Dict] = []

# External APIs
CAT_FACTS_API = "https://catfact.ninja/facts"
CAT_BREEDS_API = "https://api.thecatapi.com/v1/breeds"
CAT_IMAGES_API = "https://api.thecatapi.com/v1/images/search"

# TheCatAPI requires an API key for some endpoints, but breed and image search work without key, 
# however to avoid rate limits you might consider setting one.
# TODO: Consider adding API key header if rate limited or for extended usage


async def fetch_cat_facts(limit: int = 5) -> List[str]:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(CAT_FACTS_API, params={"limit": limit})
            resp.raise_for_status()
            data = resp.json()
            return [fact["fact"] for fact in data.get("data", [])]
    except Exception as e:
        logger.exception("Failed to fetch cat facts")
        return []


async def fetch_cat_breeds(filter_breed: Optional[str] = None) -> List[Dict]:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(CAT_BREEDS_API)
            resp.raise_for_status()
            breeds = resp.json()
            if filter_breed:
                breeds = [b for b in breeds if filter_breed.lower() in b.get("name", "").lower()]
            # Simplify breed info
            return [
                {
                    "name": b.get("name"),
                    "origin": b.get("origin"),
                    "description": b.get("description")
                }
                for b in breeds
            ]
    except Exception as e:
        logger.exception("Failed to fetch cat breeds")
        return []


async def fetch_cat_images(limit: int = 5) -> List[str]:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # TheCatAPI /images/search supports limit param
            resp = await client.get(CAT_IMAGES_API, params={"limit": limit})
            resp.raise_for_status()
            images = resp.json()
            return [img.get("url") for img in images if img.get("url")]
    except Exception as e:
        logger.exception("Failed to fetch cat images")
        return []


async def process_fetch_data(data: Dict):
    """
    Processes /cats/fetch-data POST request data:
    - Invokes external APIs based on requested types
    - Applies filters (currently only breed filter for breeds)
    - Stores aggregated data in cached_cat_data
    """
    requested_types = data.get("types", [])
    filters = data.get("filters") or {}

    results = {}

    # Fire all fetches concurrently
    tasks = []

    if "facts" in requested_types:
        tasks.append(fetch_cat_facts())

    if "breeds" in requested_types:
        breed_filter = filters.get("breed")
        tasks.append(fetch_cat_breeds(breed_filter))

    if "images" in requested_types:
        tasks.append(fetch_cat_images())

    # Await all concurrently
    fetched_data = await asyncio.gather(*tasks)

    idx = 0
    if "facts" in requested_types:
        facts = fetched_data[idx]
        cached_cat_data["facts"] = facts
        results["facts"] = facts
        idx += 1

    if "breeds" in requested_types:
        breeds = fetched_data[idx]
        cached_cat_data["breeds"] = breeds
        results["breeds"] = breeds
        idx += 1

    if "images" in requested_types:
        images = fetched_data[idx]
        cached_cat_data["images"] = images
        results["images"] = images
        idx += 1

    return results


@app.route("/cats/fetch-data", methods=["POST"])
async def cats_fetch_data():
    try:
        data = await request.get_json(force=True)
        requested_at = datetime.utcnow().isoformat()
        job_id = f"job_{requested_at}"

        # Fire-and-forget processing task that updates cached data
        # Here we await it directly because prototype should respond with data after fetch
        # In a real event-driven system, this might be async background task
        result = await process_fetch_data(data)

        return jsonify(result)
    except Exception as e:
        logger.exception("Error in /cats/fetch-data")
        return jsonify({"error": "Failed to fetch cat data"}), 500


@app.route("/cats/results", methods=["GET"])
async def cats_results():
    try:
        data_type = request.args.get("type")
        if data_type not in cached_cat_data:
            return jsonify({"error": f"Invalid type '{data_type}'. Must be one of facts, images, breeds."}), 400

        return jsonify({
            "type": data_type,
            "data": cached_cat_data.get(data_type, [])
        })
    except Exception as e:
        logger.exception("Error in /cats/results")
        return jsonify({"error": "Failed to retrieve cat data"}), 500


@app.route("/cats/favorite", methods=["POST"])
async def cats_favorite():
    try:
        data = await request.get_json(force=True)
        fav_type = data.get("type")
        content = data.get("content")

        if fav_type not in ("image", "fact") or not content:
            return jsonify({"error": "Invalid favorite submission"}), 400

        fav_record = {
            "type": fav_type,
            "content": content,
            "submittedAt": datetime.utcnow().isoformat()
        }
        favorites.append(fav_record)
        logger.info(f"Favorite saved: {fav_record}")

        return jsonify({"status": "success", "message": "Favorite saved."})
    except Exception as e:
        logger.exception("Error in /cats/favorite")
        return jsonify({"error": "Failed to save favorite"}), 500


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
