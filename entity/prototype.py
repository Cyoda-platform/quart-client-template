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

# In-memory "persistence" for fetched cat data
cats_storage: List[Dict] = []
entity_job: Dict[str, Dict] = {}

# External Petstore API base URL (public Petstore Swagger example)
PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

# Helper: simulate generating a unique job id
def generate_job_id() -> str:
    return datetime.utcnow().strftime("%Y%m%d%H%M%S%f")

# Helper: transform external pet data to internal cat model
def transform_pet_to_cat(pet: Dict) -> Dict:
    # TODO: Petstore API does not have real cat data; mapping with placeholders.
    # We'll simulate cats as pets with category.name == 'cats' or type 'cat' in tags,
    # but Petstore API has limited data, so just map all pets as cats for prototype.
    return {
        "id": str(pet.get("id")),
        "name": pet.get("name", "Unknown Cat"),
        "breed": pet.get("category", {}).get("name", "Unknown Breed"),
        "age": pet.get("age", 2),  # TODO: No age in Petstore API, use dummy
        "description": pet.get("description", "No description available"),
        "imageUrl": pet.get("photoUrls", [None])[0] if pet.get("photoUrls") else None,
    }

async def fetch_cats_from_petstore(filters: Dict) -> List[Dict]:
    """
    Fetch pets from Petstore API and filter to simulate cats.
    Petstore API doesn't have real cats, so we fetch pets and treat them as cats.
    """
    async with httpx.AsyncClient() as client:
        try:
            # Petstore API provides /pet/findByStatus?status=available
            # We'll fetch available pets and treat them as cats.
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": "available"})
            resp.raise_for_status()
            pets = resp.json()

            # Filter by breed if specified (breed mapped from category.name)
            breed_filter = filters.get("breed")
            age_min = filters.get("ageRange", {}).get("min")
            age_max = filters.get("ageRange", {}).get("max")
            limit = filters.get("limit") or 10

            cats = []
            for pet in pets:
                # Transform pet to cat model
                cat = transform_pet_to_cat(pet)

                # Breed filter
                if breed_filter and breed_filter.lower() != cat["breed"].lower():
                    continue

                # Age filter - using dummy age, so just check if provided
                if age_min is not None and cat["age"] < age_min:
                    continue
                if age_max is not None and cat["age"] > age_max:
                    continue

                cats.append(cat)
                if len(cats) >= limit:
                    break

            return cats

        except httpx.HTTPError as e:
            logger.exception("Failed to fetch cats from Petstore API")
            return []

async def process_entity(job_id: str, filters: Dict):
    """
    Background task to fetch cats and store them.
    """
    try:
        cats = await fetch_cats_from_petstore(filters)
        # Store fetched cats in global storage (overwrite for simplicity)
        global cats_storage
        cats_storage = cats
        entity_job[job_id]["status"] = "completed"
        entity_job[job_id]["fetchedCount"] = len(cats)
        entity_job[job_id]["completedAt"] = datetime.utcnow().isoformat()
        logger.info(f"Job {job_id} completed: fetched {len(cats)} cats")
    except Exception as e:
        entity_job[job_id]["status"] = "failed"
        entity_job[job_id]["error"] = str(e)
        logger.exception(f"Job {job_id} failed")

@app.route("/cats/fetch", methods=["POST"])
async def fetch_cats():
    data = await request.get_json(force=True)
    job_id = generate_job_id()
    requested_at = datetime.utcnow().isoformat()

    entity_job[job_id] = {"status": "processing", "requestedAt": requested_at}
    # Fire and forget the processing task
    asyncio.create_task(process_entity(job_id, data))

    return jsonify({
        "status": "processing",
        "jobId": job_id,
        "message": "Fetching cats from Petstore API started"
    }), 202

@app.route("/cats", methods=["GET"])
async def get_cats():
    # Parse query params
    breed = request.args.get("breed")
    age_min = request.args.get("ageMin", type=int)
    age_max = request.args.get("ageMax", type=int)
    limit = request.args.get("limit", default=10, type=int)

    filtered_cats = cats_storage

    if breed:
        filtered_cats = [c for c in filtered_cats if c.get("breed", "").lower() == breed.lower()]
    if age_min is not None:
        filtered_cats = [c for c in filtered_cats if c.get("age", 0) >= age_min]
    if age_max is not None:
        filtered_cats = [c for c in filtered_cats if c.get("age", 0) <= age_max]

    return jsonify(filtered_cats[:limit])

@app.route("/cats/search", methods=["POST"])
async def search_cats():
    data = await request.get_json(force=True)
    filters = data.get("filters", {})
    sort_by = data.get("sortBy")
    limit = data.get("limit") or 10

    # Apply filters on stored cats
    result_cats = cats_storage

    breed = filters.get("breed")
    age_range = filters.get("ageRange", {})
    name_contains = filters.get("nameContains")

    if breed:
        result_cats = [c for c in result_cats if c.get("breed", "").lower() == breed.lower()]
    if age_range:
        min_age = age_range.get("min")
        max_age = age_range.get("max")
        if min_age is not None:
            result_cats = [c for c in result_cats if c.get("age", 0) >= min_age]
        if max_age is not None:
            result_cats = [c for c in result_cats if c.get("age", 0) <= max_age]
    if name_contains:
        result_cats = [c for c in result_cats if name_contains.lower() in c.get("name", "").lower()]

    if sort_by in {"age", "breed", "name"}:
        try:
            result_cats = sorted(result_cats, key=lambda c: c.get(sort_by) or "")
        except Exception as e:
            logger.exception("Sorting failed")

    return jsonify(result_cats[:limit])

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```
