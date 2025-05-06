from dataclasses import dataclass
import logging

import httpx
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

PET_ENTITY_NAME = "pet"
PETSTORE_API_BASE = "https://petstore3.swagger.io/api/v3"

@dataclass
class PetIdRequest:
    petId: int

def is_valid_pet_id(pet_id):
    return isinstance(pet_id, int) and pet_id > 0

async def fetch_pet_from_external_api(pet_id: int):
    url = f"{PETSTORE_API_BASE}/pet/{pet_id}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            return {
                "petId": data.get("id"),
                "name": data.get("name"),
                "category": data.get("category", {}).get("name") if data.get("category") else None,
                "status": data.get("status"),
                "photoUrls": data.get("photoUrls", []),
            }, None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None, "Pet not found."
            logger.exception(f"HTTP error fetching pet {pet_id}")
            return None, "Failed to fetch pet details."
        except Exception:
            logger.exception(f"Unexpected error fetching pet {pet_id}")
            return None, "Unexpected error occurred."

# Workflow function for 'pet' entity
async def process_pet(entity):
    """
    Workflow function applied to 'pet' entity before persisting.
    Fetches pet details from external API and updates entity in-place.
    """
    pet_id = entity.get("petId")
    if not pet_id:
        entity["status"] = "error"
        entity["errorMessage"] = "Missing petId in entity."
        return entity

    # Fetch external pet details
    pet_data, error = await fetch_pet_from_external_api(pet_id)

    if pet_data:
        # Update entity with full pet data and status 'ready'
        entity.update(pet_data)
        entity["status"] = "ready"
        # Remove any previous error message
        entity.pop("errorMessage", None)
    else:
        # Update entity with error info and status 'error'
        entity["status"] = "error"
        entity["errorMessage"] = error

    return entity

@app.route("/pets/details", methods=["POST"])
@validate_request(PetIdRequest)
async def retrieve_pet_details(data: PetIdRequest):
    pet_id = data.petId
    if not is_valid_pet_id(pet_id):
        return jsonify({"error": "Invalid pet ID format."}), 400

    # Initial entity state with minimal data and status 'processing'
    initial_entity = {
        "petId": pet_id,
        "status": "processing"
    }

    try:
        # Add entity with workflow that fetches and enriches data before persistence
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=initial_entity,
            workflow=process_pet
        )
    except Exception as e:
        logger.exception(f"Failed to initiate pet details processing for petId {pet_id}: {e}")
        return jsonify({"error": "Failed to initiate pet details request."}), 500

    return jsonify({
        "message": "Pet details request accepted and processing.",
        "petId": pet_id
    }), 202

@app.route("/pets/details/<int:pet_id>", methods=["GET"])
async def get_cached_pet_details(pet_id):
    try:
        item = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=str(pet_id)
        )
    except Exception as e:
        logger.exception(f"Failed to retrieve pet details for petId {pet_id}: {e}")
        return jsonify({
            "error": "Pet details not found. Please submit a POST request first."
        }), 404

    if not item:
        return jsonify({
            "error": "Pet details not found. Please submit a POST request first."
        }), 404

    status = item.get("status")
    if status == "processing":
        return jsonify({
            "message": "Pet details are still being processed. Please try again shortly."
        }), 202

    if status == "error":
        return jsonify({
            "error": item.get("errorMessage", "Failed to retrieve pet details.")
        }), 500

    # status == 'ready' or otherwise return the pet data
    return jsonify(item), 200


if __name__ == '__main__':
    import sys
    import logging

    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)