from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

pet_cache = {}

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
            pet_data = {
                "petId": data.get("id"),
                "name": data.get("name"),
                "category": data.get("category", {}).get("name") if data.get("category") else None,
                "status": data.get("status"),
                "photoUrls": data.get("photoUrls", []),
            }
            return pet_data, None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None, {"error": "Pet not found."}
            logger.exception(f"HTTP error when fetching pet {pet_id}")
            return None, {"error": "Failed to fetch pet details from external API."}
        except Exception as e:
            logger.exception(f"Unexpected error when fetching pet {pet_id}")
            return None, {"error": "Unexpected error occurred during fetch."}

async def process_pet_request(pet_id: int):
    pet_data, error = await fetch_pet_from_external_api(pet_id)
    if pet_data:
        pet_cache[pet_id] = pet_data
    else:
        pet_cache[pet_id] = error

@app.route("/pets/details", methods=["POST"])
@validate_request(PetIdRequest)  # validation last in POST - issue workaround
async def retrieve_pet_details(data: PetIdRequest):
    pet_id = data.petId
    if not is_valid_pet_id(pet_id):
        return jsonify({"error": "Invalid pet ID format."}), 400

    requested_at = datetime.utcnow().isoformat()
    pet_cache[pet_id] = {"status": "processing", "requestedAt": requested_at}
    asyncio.create_task(process_pet_request(pet_id))

    return jsonify({
        "message": "Pet details request accepted and processing.",
        "petId": pet_id,
        "requestedAt": requested_at,
    }), 202

@app.route("/pets/details/<int:pet_id>", methods=["GET"])
# No validation decorator here because GET without query params or body
async def get_cached_pet_details(pet_id):
    if pet_id not in pet_cache:
        return jsonify({
            "error": "Pet details not found. Please submit a POST request first."
        }), 404

    cached = pet_cache[pet_id]
    if cached.get("status") == "processing":
        return jsonify({
            "message": "Pet details are still being processed. Please try again shortly.",
            "requestedAt": cached.get("requestedAt")
        }), 202

    return jsonify(cached), 200


if __name__ == '__main__':
    import sys
    import logging

    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
