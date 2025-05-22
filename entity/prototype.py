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

# Local in-memory caches
# Structure:
# pets_cache: Dict[int, dict] - petId -> pet data
# adoption_requests: Dict[str, dict] - requestId -> adoption request data
pets_cache: Dict[int, dict] = {}
adoption_requests: Dict[str, dict] = {}
# Entity job status cache for fetch tasks, keyed by job_id (UUID str)
entity_jobs: Dict[str, dict] = {}

# External Petstore API base URL (Swagger Petstore example)
PETSTORE_API_BASE = "https://petstore.swagger.io/v2"


async def fetch_external_pets(
    status_filter: Optional[str], type_filter: Optional[str], limit: int
) -> List[dict]:
    """
    Fetch pets from the external Petstore API filtered by status and type.
    The Petstore API does not have direct filtering endpoints for status/type,
    so we fetch all by status and filter by type here.

    TODO: Petstore API has limited filtering; real filtering might require more logic.
    """
    pets = []
    async with httpx.AsyncClient(timeout=10) as client:
        # Petstore API endpoint to find pets by status (comma separated)
        # If no status_filter provided, fetch all statuses (available,pending,sold)
        statuses = status_filter if status_filter else "available,pending,sold"
        params = {"status": statuses}
        try:
            r = await client.get(f"{PETSTORE_API_BASE}/pet/findByStatus", params=params)
            r.raise_for_status()
            all_pets = r.json()
            # Filter by type if specified
            if type_filter:
                for pet in all_pets:
                    # Pet type is in pet['category']['name'] if exists
                    pet_type = pet.get("category", {}).get("name", "").lower()
                    if pet_type == type_filter.lower():
                        pets.append(pet)
                    if len(pets) >= limit:
                        break
            else:
                pets = all_pets[:limit]
        except Exception as e:
            logger.exception("Failed to fetch pets from external API")
            raise e
    return pets


async def process_and_cache_pets(
    filters: dict, sort_by: Optional[str], limit: int, job_id: str
) -> None:
    """
    Async background task to fetch, process, and cache pets.
    Updates the entity_jobs[job_id] status on finish.
    """
    try:
        status_filter = filters.get("status") if filters else None
        type_filter = filters.get("type") if filters else None

        pets = await fetch_external_pets(status_filter, type_filter, limit)

        # Simplify pet data and cache by pet id (use pet['id'])
        # Sorting if requested (only by 'name' or 'dateAdded' - dateAdded is not available in Petstore API, so ignore)
        def pet_sort_key(p):
            if sort_by == "name":
                return p.get("name", "").lower()
            # No dateAdded in Petstore API; fallback
            return 0

        if sort_by in ("name",):
            pets.sort(key=pet_sort_key)

        # Cache pets
        pets_cache.clear()
        for pet in pets:
            pets_cache[pet["id"]] = {
                "id": pet["id"],
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name", "unknown"),
                "status": pet.get("status"),
                # Age not available in Petstore API - TODO: Placeholder for age
                "age": None,
                # Additional details stored for detail endpoint
                "description": pet.get("description", ""),
                "photos": pet.get("photoUrls", []),
            }

        entity_jobs[job_id]["status"] = "completed"
        entity_jobs[job_id]["count"] = len(pets_cache)
        entity_jobs[job_id]["completedAt"] = datetime.utcnow().isoformat()
        logger.info(f"Pets data fetched and cached successfully, count={len(pets_cache)}")
    except Exception as e:
        entity_jobs[job_id]["status"] = "failed"
        entity_jobs[job_id]["error"] = str(e)
        logger.exception("Error processing pets data")


@app.route("/pets/fetch", methods=["POST"])
async def fetch_pets():
    """
    POST /pets/fetch
    Request body example:
    {
      "filters": {
        "status": "available",
        "type": "cat"
      },
      "sortBy": "name",
      "limit": 50
    }
    """
    data = await request.get_json(force=True)
    filters = data.get("filters", {})
    sort_by = data.get("sortBy")
    limit = data.get("limit", 50)
    # Validate limit upper bound
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        limit = 50

    job_id = datetime.utcnow().isoformat() + "-" + str(id(data))
    entity_jobs[job_id] = {
        "status": "processing",
        "requestedAt": datetime.utcnow().isoformat(),
    }

    # Fire and forget the processing task
    asyncio.create_task(process_and_cache_pets(filters, sort_by, limit, job_id))

    return jsonify(
        {
            "message": "Pets data fetching started",
            "jobId": job_id,
            "status": entity_jobs[job_id]["status"],
        }
    )


@app.route("/pets", methods=["GET"])
async def get_pets():
    """
    GET /pets
    Returns list of cached pets.
    """
    pets_list = []
    for pet in pets_cache.values():
        pets_list.append(
            {
                "id": pet["id"],
                "name": pet["name"],
                "type": pet["type"],
                "status": pet["status"],
                "age": pet["age"],
            }
        )
    return jsonify(pets_list)


@app.route("/pets/<int:pet_id>", methods=["GET"])
async def get_pet_details(pet_id: int):
    """
    GET /pets/{petId}
    Returns detailed info about a pet from cache.
    """
    pet = pets_cache.get(pet_id)
    if not pet:
        return jsonify({"error": "Pet not found"}), 404
    return jsonify(pet)


@app.route("/adoptions", methods=["POST"])
async def create_adoption():
    """
    POST /adoptions
    Request body example:
    {
      "petId": 1,
      "user": {
        "name": "John Doe",
        "email": "john@example.com"
      }
    }
    """
    data = await request.get_json(force=True)
    pet_id = data.get("petId")
    user = data.get("user")
    if not pet_id or not user or not user.get("name") or not user.get("email"):
        return jsonify({"error": "Invalid request data"}), 400
    if pet_id not in pets_cache:
        return jsonify({"error": "Pet not found"}), 404

    # Generate a simple request ID
    request_id = f"req-{datetime.utcnow().timestamp()}-{pet_id}"

    # Save adoption request in local cache (mock persistence)
    adoption_requests[request_id] = {
        "requestId": request_id,
        "petId": pet_id,
        "user": user,
        "status": "submitted",
        "submittedAt": datetime.utcnow().isoformat(),
    }

    logger.info(f"Adoption request submitted: {request_id} for pet {pet_id} by {user.get('name')}")

    return jsonify({"message": "Adoption request submitted successfully", "requestId": request_id})


if __name__ == "__main__":
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
