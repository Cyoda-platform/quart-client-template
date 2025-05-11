```python
import asyncio
import logging
from datetime import datetime
from typing import List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# --- In-memory "cache" ---
cat_data_cache = []  # list of dicts with cat data
breeds_cache = []    # list of dicts with breed data

# --- External API info ---
CAT_API_BASE = "https://api.thecatapi.com/v1"
CAT_API_BREEDS = f"{CAT_API_BASE}/breeds"
CAT_API_IMAGES_SEARCH = f"{CAT_API_BASE}/images/search"

# For public access, TheCatAPI allows limited calls w/o key, no key used here for prototype.
# TODO: If rate-limited, consider adding API key.

# Utility: fetch breeds list from external API
async def fetch_breeds() -> List[dict]:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(CAT_API_BREEDS)
            resp.raise_for_status()
            breeds = resp.json()
            # Normalize breeds info for cache
            normalized = []
            for b in breeds:
                normalized.append(
                    {
                        "id": b.get("id"),
                        "name": b.get("name"),
                        "description": b.get("description") or "",
                        "origin": b.get("origin") or "",
                    }
                )
            return normalized
        except Exception as e:
            logger.exception(e)
            return []

# Utility: fetch cat images + breed info; can filter by breed id (TheCatAPI breed id)
async def fetch_cats(breed: Optional[str] = None, limit: int = 25) -> List[dict]:
    async with httpx.AsyncClient() as client:
        try:
            params = {"limit": limit}
            if breed:
                params["breed_ids"] = breed

            resp = await client.get(CAT_API_IMAGES_SEARCH, params=params)
            resp.raise_for_status()
            images = resp.json()

            cats = []
            for img in images:
                breeds = img.get("breeds") or []
                breed_info = breeds[0] if breeds else {}
                cats.append(
                    {
                        "id": img.get("id"),
                        "name": breed_info.get("name", "Unknown"),
                        "image_url": img.get("url"),
                        "description": breed_info.get("description", ""),
                    }
                )
            return cats
        except Exception as e:
            logger.exception(e)
            return []

# --- Business logic tasks ---

async def process_fetch_cats(data: dict):
    breed = data.get("breed")
    cats = await fetch_cats(breed=breed)
    global cat_data_cache
    cat_data_cache = cats
    logger.info(f"Cached {len(cats)} cats (breed filter: {breed})")

async def process_fetch_breeds():
    breeds = await fetch_breeds()
    global breeds_cache
    breeds_cache = breeds
    logger.info(f"Cached {len(breeds)} cat breeds")

# --- Endpoint implementations ---

@app.route("/cats/fetch", methods=["POST"])
async def cats_fetch():
    try:
        data = await request.get_json(force=True)
    except Exception:
        data = {}

    # Fire and forget processing task
    await asyncio.create_task(process_fetch_cats(data))

    return jsonify({
        "status": "success",
        "message": "Data fetch triggered, caching in progress",
        "count": len(cat_data_cache),
    })

@app.route("/cats", methods=["GET"])
async def cats_get():
    breed = request.args.get("breed")
    if breed:
        filtered = [c for c in cat_data_cache if c.get("name").lower() == breed.lower()]
    else:
        filtered = cat_data_cache
    return jsonify(filtered)

@app.route("/cats/breeds", methods=["POST"])
async def breeds_fetch():
    await asyncio.create_task(process_fetch_breeds())
    return jsonify({
        "status": "success",
        "message": "Breeds fetch triggered, caching in progress",
        "count": len(breeds_cache),
    })

@app.route("/cats/breeds", methods=["GET"])
async def breeds_get():
    return jsonify(breeds_cache)

if __name__ == "__main__":
    import sys
    import logging

    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
