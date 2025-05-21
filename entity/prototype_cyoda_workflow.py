Here's the updated complete code with the `workflow` parameter added to `entity_service.add_item` calls and appropriate workflow functions implemented according to your specification:

```python
import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

# --- Workflow functions ---

async def process_pet_search_request(entity):
    """
    Workflow function for pet_search_request entity.
    You can modify entity state here before persistence.
    """
    # For example, initialize status if not set
    if "status" not in entity:
        entity["status"] = "processing"
    # Could trigger some async processing here if needed
    return entity

async def process_pet_detail(entity):
    """
    Workflow function for pet_detail entity.
    You can modify entity state here before persistence.
    """
    # Example: Ensure status field exists
    if "status" not in entity:
        entity["status"] = "processing"
    return entity

# Request schemas
@dataclass
class PetSearchRequest:
    status: str
    category: Optional[str] = None

@dataclass
class PetDetailsRequest:
    petIds: List[str]  # changed from int to str for id compliance

@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearchRequest)
async def pets_search(data: PetSearchRequest):
    search_data = {
        "status": data.status,
        "category": data.category
    }
    try:
        search_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet_search_request",
            entity_version=ENTITY_VERSION,
            entity=search_data,
            workflow=process_pet_search_request  # Added workflow function
        )
    except Exception as e:
        logger.exception(f"Failed to add pet_search_request item: {e}")
        return jsonify({"error": "Failed to process search request"}), 500
    return jsonify({"searchId": search_id})

@app.route("/pets/search/<string:search_id>", methods=["GET"])
async def get_search_results(search_id):
    try:
        entry = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet_search_request",
            entity_version=ENTITY_VERSION,
            technical_id=search_id
        )
    except Exception as e:
        logger.exception(f"Error retrieving pet_search_request with id {search_id}: {e}")
        return jsonify({"error": "searchId not found"}), 404

    if not entry:
        return jsonify({"error": "searchId not found"}), 404

    status = entry.get("status")
    if status == "processing":
        return jsonify({"searchId": search_id, "status": "processing", "results": None}), 202
    if status == "failed":
        return jsonify({"searchId": search_id, "status": "failed", "results": None}), 500

    results = entry.get("results")
    return jsonify({"searchId": search_id, "results": results})

@app.route("/pets/details", methods=["POST"])
@validate_request(PetDetailsRequest)
async def pets_details(data: PetDetailsRequest):
    pet_ids = data.petIds
    pets_response = []

    async def fetch_and_enrich_pet(pet_id: str):
        try:
            pet_data = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="pet_detail",
                entity_version=ENTITY_VERSION,
                technical_id=pet_id
            )
            if pet_data and pet_data.get("status") == "completed" and pet_data.get("data"):
                return pet_data["data"]
            # If no cached data or not completed, fetch from external API
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"https://petstore.swagger.io/v2/pet/{pet_id}")
                resp.raise_for_status()
                pet = resp.json()
                name = pet.get("name", "Mysterious Pet")
                category = pet.get("category", {}).get("name", "Unknown Category")
                status = pet.get("status", "unknown")
                fun_description = f"{name} is a wonderful {category.lower()} currently {status} and waiting for a loving home! 😻"
                enriched = {
                    "id": pet_id,
                    "name": name,
                    "category": category,
                    "status": status,
                    "funDescription": fun_description,
                }
                # Save enriched data with status completed
                entity_payload = {
                    "status": "completed",
                    "data": enriched
                }
                try:
                    await entity_service.update_item(
                        token=cyoda_auth_service,
                        entity_model="pet_detail",
                        entity_version=ENTITY_VERSION,
                        entity=entity_payload,
                        technical_id=pet_id,
                        meta={}
                    )
                except Exception as e:
                    logger.exception(f"Failed to update pet_detail for {pet_id}: {e}")
                return enriched
        except Exception as e:
            # On error, update status to failed
            logger.exception(f"Failed to fetch/enrich pet details for {pet_id}: {e}")
            try:
                await entity_service.update_item(
                    token=cyoda_auth_service,
                    entity_model="pet_detail",
                    entity_version=ENTITY_VERSION,
                    entity={"status": "failed", "data": None},
                    technical_id=pet_id,
                    meta={}
                )
            except Exception as ee:
                logger.exception(f"Failed to update failed status for pet_detail {pet_id}: {ee}")
            return None

    tasks = [fetch_and_enrich_pet(pid) for pid in pet_ids]
    results = await asyncio.gather(*tasks)
    pets_response = [pet for pet in results if pet is not None]
    return jsonify({"pets": pets_response})

@app.route("/pets/details/<string:pet_id>", methods=["GET"])
async def get_pet_details(pet_id):
    try:
        entry = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet_detail",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
    except Exception as e:
        logger.exception(f"Error retrieving pet_detail with id {pet_id}: {e}")
        return jsonify({"error": "petId not found"}), 404

    if not entry:
        return jsonify({"error": "petId not found"}), 404

    status = entry.get("status")
    if status == "processing":
        return jsonify({"petId": pet_id, "status": "processing", "data": None}), 202
    if status == "failed":
        return jsonify({"petId": pet_id, "status": "failed", "data": None}), 500

    return jsonify(entry.get("data"))

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```

### Summary of changes:
- Added two async workflow functions:
  - `process_pet_search_request` for `"pet_search_request"`
  - `process_pet_detail` for `"pet_detail"`
- Added `workflow=process_pet_search_request` to the `entity_service.add_item` call for `"pet_search_request"`.
- If you add more `add_item` calls for other entities in the future, add similar workflow functions following the `process_{entity_name}` naming convention, where the entity name is underscore lowercase.

Let me know if you want me to add workflows for any other entities or further customize these!