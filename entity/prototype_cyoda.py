from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

# In-memory job tracking for async processing (prototype pattern)
entity_job: Dict[int, dict] = {}

PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"

@dataclass
class PetIdRequest:
    petId: int

async def fetch_pet_from_external_api(pet_id: int) -> dict:
    """Call external Petstore API to retrieve pet details by pet ID."""
    url = f"{PETSTORE_BASE_URL}/pet/{pet_id}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            # Validate required fields from response
            if "id" not in data:
                raise ValueError("Invalid response structure: missing 'id'")
            return data
        except httpx.HTTPStatusError as e:
            # Pet not found or other HTTP errors
            logger.exception(f"HTTP error fetching pet {pet_id}: {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error fetching pet {pet_id}: {e}")
            raise

async def process_pet_entity(pet_id: int):
    """Fetch pet details from external API and add to entity_service, update job status."""
    job = entity_job.get(pet_id)
    try:
        pet_data = await fetch_pet_from_external_api(pet_id)
        # Simplify and extract only required fields for entity data
        pet_summary = {
            "id": pet_data.get("id"),
            "name": pet_data.get("name"),
            "category": pet_data.get("category", {}).get("name") if pet_data.get("category") else None,
            "status": pet_data.get("status"),
            "photoUrls": pet_data.get("photoUrls", []),
        }
        # Add item to entity_service
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=pet_summary
        )
        if job:
            job["status"] = "completed"
            job["completedAt"] = datetime.utcnow().isoformat()
    except Exception as e:
        if job:
            job["status"] = "failed"
            job["error"] = str(e)
        logger.exception(f"Failed to process pet entity for petId={pet_id}")

@app.route("/api/pets/details", methods=["POST"])
@validate_request(PetIdRequest)  # validation last on POST (issue workaround)
async def post_pet_details(data: PetIdRequest):
    """
    Accepts JSON body with 'petId', triggers async fetch from external API,
    and returns job status or error.
    """
    pet_id = data.petId

    if not isinstance(pet_id, int) or pet_id <= 0:
        return jsonify({"status": "error", "message": "Invalid petId provided"}), 400

    # Check if pet already exists in entity_service by condition
    try:
        existing_items = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            condition={"id": pet_id}
        )
        if existing_items:
            # Return the first matched pet data directly
            return jsonify({"status": "success", "pet": existing_items[0]}), 200
    except Exception as e:
        logger.exception(f"Error checking existing pet in entity_service: {e}")
        # Proceed to fetch if error occurs

    # Start async processing job
    requested_at = datetime.utcnow().isoformat()
    entity_job[pet_id] = {"status": "processing", "requestedAt": requested_at}

    # Fire and forget the processing task
    asyncio.create_task(process_pet_entity(pet_id))

    return jsonify({
        "status": "processing",
        "message": "Pet details retrieval started. Please query GET /api/pets/details/{petId} to check result.",
        "petId": pet_id
    }), 202

@app.route("/api/pets/details/<int:pet_id>", methods=["GET"])
# No request body, no validation needed for GET with path param (issue workaround)
async def get_pet_details(pet_id: int):
    """Return cached pet details or appropriate error message."""
    # Try to get pet details from entity_service
    try:
        items = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            condition={"id": pet_id}
        )
        if items:
            return jsonify({"pet": items[0]}), 200
    except Exception as e:
        logger.exception(f"Error fetching pet details from entity_service: {e}")
        return jsonify({
            "status": "error",
            "message": "Error fetching pet details."
        }), 500

    job = entity_job.get(pet_id)
    if job:
        if job.get("status") == "processing":
            return jsonify({
                "status": "processing",
                "message": "Pet details are being fetched. Please try again shortly."
            }), 202
        elif job.get("status") == "failed":
            return jsonify({
                "status": "error",
                "message": f"Failed to fetch pet details: {job.get('error')}"
            }), 500

    return jsonify({
        "status": "error",
        "message": "Pet details not found. Please fetch via POST /api/pets/details first."
    }), 404

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)