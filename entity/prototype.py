import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request  # validate_request last for POST, validate_querystring first for GET

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

@dataclass
class PetsSearch:
    category: Optional[str]
    status: Optional[str]

# Local in-memory cache for prototype (async-safe usage via asyncio.Lock)
class Cache:
    def __init__(self):
        self._pets: Optional[Dict[str, Any]] = None
        self._categories: Optional[Dict[str, Any]] = None
        self._lock = asyncio.Lock()

    async def set_pets(self, pets_data: Dict[str, Any]):
        async with self._lock:
            self._pets = pets_data

    async def get_pets(self) -> Optional[Dict[str, Any]]:
        async with self._lock:
            return self._pets

    async def set_categories(self, categories_data: Dict[str, Any]):
        async with self._lock:
            self._categories = categories_data

    async def get_categories(self) -> Optional[Dict[str, Any]]:
        async with self._lock:
            return self._categories


cache = Cache()

PETSTORE_BASE = "https://petstore.swagger.io/v2"

# Helper function to fetch categories from Petstore API
async def fetch_petstore_categories() -> Dict[str, Any]:
    url = f"{PETSTORE_BASE}/store/inventory"
    # Petstore does not provide direct categories endpoint, so workaround:
    # TODO: Petstore API lacks a categories endpoint, so we mock categories from pets data.
    async with httpx.AsyncClient() as client:
        try:
            pets_resp = await client.get(f"{PETSTORE_BASE}/pet/findByStatus", params={"status": "available"})
            pets_resp.raise_for_status()
            pets = pets_resp.json()
        except Exception as e:
            logger.exception(e)
            return {"categories": []}

    category_set = set()
    for pet in pets:
        cat = pet.get("category")
        if cat and isinstance(cat, dict) and "name" in cat:
            category_set.add((cat.get("id", 0), cat["name"]))
    categories = [{"id": cid, "name": name} for cid, name in category_set]
    return {"categories": categories}


# Helper function to fetch pets from Petstore API with filters
async def fetch_petstore_pets(category_name: Optional[str], status: Optional[str]) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        try:
            params = {}
            if status:
                params["status"] = status
            statuses = [status] if status else ["available", "pending", "sold"]

            all_filtered_pets = []
            for st in statuses:
                resp = await client.get(f"{PETSTORE_BASE}/pet/findByStatus", params={"status": st})
                resp.raise_for_status()
                pets = resp.json()
                if category_name:
                    pets = [
                        pet for pet in pets
                        if pet.get("category") and pet["category"].get("name") == category_name
                    ]
                all_filtered_pets.extend(pets)

            pets_out = []
            for pet in all_filtered_pets:
                pets_out.append({
                    "id": pet.get("id"),
                    "name": pet.get("name"),
                    "category": pet.get("category", {}).get("name") if pet.get("category") else None,
                    "status": pet.get("status"),
                    "photoUrls": pet.get("photoUrls", []),
                })

            return {"pets": pets_out}
        except Exception as e:
            logger.exception(e)
            return {"pets": []}


@app.route("/categories/fetch", methods=["POST"])
async def categories_fetch():
    requested_at = datetime.utcnow().isoformat()
    logger.info(f"Categories fetch requested at {requested_at}")

    async def process_categories():
        data = await fetch_petstore_categories()
        await cache.set_categories(data)
        logger.info("Categories cached successfully")

    asyncio.create_task(process_categories())
    return jsonify({"status": "processing", "requestedAt": requested_at}), 202


@app.route("/categories", methods=["GET"])
async def categories_get():
    cats = await cache.get_categories()
    if cats is None:
        return jsonify({"categories": [], "message": "No categories cached yet"}), 404
    return jsonify(cats)


@app.route("/pets/search", methods=["POST"])
@validate_request(PetsSearch)  # workaround: place validation last for POST
async def pets_search(data: PetsSearch):
    category = data.category
    status = data.status
    requested_at = datetime.utcnow().isoformat()
    logger.info(f"Pets search requested at {requested_at} with category={category} status={status}")

    async def process_pets():
        pets_data = await fetch_petstore_pets(category, status)
        await cache.set_pets(pets_data)
        logger.info("Pets search results cached")

    asyncio.create_task(process_pets())
    return jsonify({"status": "processing", "requestedAt": requested_at}), 202


@app.route("/pets", methods=["GET"])
async def pets_get():
    pets = await cache.get_pets()
    if pets is None:
        return jsonify({"pets": [], "message": "No pets cached yet"}), 404
    return jsonify(pets)


if __name__ == '__main__':
    import sys
    import logging

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)