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

# In-memory async-safe cache for pets and adoptions (simulate persistence)
class AsyncCache:
    def __init__(self):
        self._pets: List[Dict] = []
        self._adoptions: List[Dict] = []
        self._lock = asyncio.Lock()

    async def update_pets(self, pets: List[Dict]):
        async with self._lock:
            self._pets = pets

    async def get_pets(self) -> List[Dict]:
        async with self._lock:
            return list(self._pets)

    async def add_adoption(self, adoption: Dict):
        async with self._lock:
            self._adoptions.append(adoption)

    async def get_adoptions(self) -> List[Dict]:
        async with self._lock:
            return list(self._adoptions)


cache = AsyncCache()

# External Petstore API base url
PETSTORE_API_BASE = "https://petstore3.swagger.io/api/v3"

# Utility: filter pets by status and tags
def filter_pets(pets: List[Dict], status: Optional[str], tags: Optional[List[str]]) -> List[Dict]:
    filtered = pets
    if status:
        filtered = [p for p in filtered if p.get("status") == status]
    if tags:
        filtered = [p for p in filtered if "tags" in p and any(tag["name"] in tags for tag in p["tags"])]
    return filtered

# Business logic: process raw petstore data into simplified pet dicts
def process_petstore_pets(raw_pets: List[Dict]) -> List[Dict]:
    processed = []
    for pet in raw_pets:
        processed.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "status": pet.get("status"),
            "category": pet.get("category", {}).get("name") if pet.get("category") else None,
            "tags": [tag.get("name") for tag in pet.get("tags", [])] if pet.get("tags") else [],
        })
    return processed

# Async job for fetching and processing pets from external API
async def process_fetch_pets_job(status: Optional[str], tags: Optional[List[str]]):
    async with httpx.AsyncClient() as client:
        try:
            # Petstore API endpoint to find pets by status
            # The real Petstore API supports only one status at a time, so we pass status or omit filter.
            # TODO: Consider pagination if needed.
            url = f"{PETSTORE_API_BASE}/pet/findByStatus"
            params = {}
            if status:
                params["status"] = status
            else:
                # fallback to all statuses if no status specified
                params["status"] = "available,pending,sold"

            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            raw_pets = response.json()

            # Filter by tags if provided (since petstore API doesn't support tag filtering)
            filtered_pets = filter_pets(raw_pets, None, tags)

            processed = process_petstore_pets(filtered_pets)
            await cache.update_pets(processed)
            logger.info(f"Fetched and processed {len(processed)} pets from Petstore API.")
        except Exception as e:
            logger.exception("Error fetching pets from Petstore API")

@app.route("/pets/fetch", methods=["POST"])
async def fetch_pets():
    """
    POST /pets/fetch
    Request JSON:
    {
        "status": "available|pending|sold",  # optional
        "tags": ["tag1", "tag2"]             # optional
    }
    """
    data = await request.get_json(force=True)
    status = data.get("status")
    tags = data.get("tags")
    if tags and not isinstance(tags, list):
        return jsonify({"error": "'tags' must be a list of strings"}), 400

    requested_at = datetime.utcnow().isoformat()
    logger.info(f"Received /pets/fetch request at {requested_at} with status={status} and tags={tags}")

    # Fire and forget fetch & process job
    asyncio.create_task(process_fetch_pets_job(status, tags))

    return jsonify({"message": "Pets fetch job started"}), 202

@app.route("/pets", methods=["GET"])
async def get_pets():
    """
    GET /pets
    Returns the processed pet list cached in the app.
    """
    pets = await cache.get_pets()
    return jsonify(pets)

@app.route("/pets/adopt", methods=["POST"])
async def adopt_pet():
    """
    POST /pets/adopt
    Request JSON:
    {
        "petId": int,
        "adopterName": str,
        "contact": str
    }
    """
    data = await request.get_json(force=True)
    pet_id = data.get("petId")
    adopter_name = data.get("adopterName")
    contact = data.get("contact")

    if not pet_id or not adopter_name or not contact:
        return jsonify({"error": "petId, adopterName, and contact are required"}), 400

    adoption_request = {
        "requestId": int(datetime.utcnow().timestamp() * 1000),  # simplistic unique id
        "petId": pet_id,
        "adopterName": adopter_name,
        "contact": contact,
        "status": "pending",
        "requestedAt": datetime.utcnow().isoformat(),
    }

    await cache.add_adoption(adoption_request)
    logger.info(f"New adoption request: {adoption_request}")

    return jsonify({"message": "Adoption request submitted", "requestId": adoption_request["requestId"]})

@app.route("/adoptions", methods=["GET"])
async def get_adoptions():
    """
    GET /adoptions
    Returns all adoption requests.
    """
    adoptions = await cache.get_adoptions()
    return jsonify(adoptions)


if __name__ == '__main__':
    import sys
    import logging.config

    # Basic logging config to console
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        level=logging.INFO,
        stream=sys.stdout,
    )

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
