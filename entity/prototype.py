from dataclasses import dataclass
from typing import Optional
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

# --- In-memory "cache" ---
cat_data_cache = []  # list of dicts with cat data
breeds_cache = []    # list of dicts with breed data

# --- External API info ---
CAT_API_BASE = "https://api.thecatapi.com/v1"
CAT_API_BREEDS = f"{CAT_API_BASE}/breeds"
CAT_API_IMAGES_SEARCH = f"{CAT_API_BASE}/images/search"

@dataclass
class FetchCatsRequest:
    breed: Optional[str] = None

# For breeds POST no body expected; so no dataclass needed

# --- External API utilities ---

async def fetch_breeds() -> List[dict]:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(CAT_API_BREEDS)
            resp.raise_for_status()
            breeds = resp.json()
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
@validate_request(FetchCatsRequest)  # POST validation goes last (after route) per quart-schema workaround
async def cats_fetch(data: FetchCatsRequest):
    # Fire and forget processing task
    await asyncio.create_task(process_fetch_cats(data.__dict__))
    return jsonify({
        "status": "success",
        "message": "Data fetch triggered, caching in progress",
        "count": len(cat_data_cache),
    })

@app.route("/cats", methods=["GET"])
# GET validation must come first (workaround for quart-schema issue), but we have no query validation dataclass here because breed is optional and simple
async def cats_get():
    breed = request.args.get("breed")
    if breed:
        filtered = [c for c in cat_data_cache if c.get("name").lower() == breed.lower()]
    else:
        filtered = cat_data_cache
    return jsonify(filtered)

@app.route("/cats/breeds", methods=["POST"])
# No request body, so no validation decorator needed here
async def breeds_fetch():
    await asyncio.create_task(process_fetch_breeds())
    return jsonify({
        "status": "success",
        "message": "Breeds fetch triggered, caching in progress",
        "count": len(breeds_cache),
    })

@app.route("/cats/breeds", methods=["GET"])
# GET with no query parameters, no validation needed
async def breeds_get():
    return jsonify(breeds_cache)

if __name__ == "__main__":
    import sys
    import logging

    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
