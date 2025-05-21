import asyncio
import logging
from dataclasses import dataclass
from typing import List, Optional

import httpx
from quart import Quart, jsonify
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

# --- Workflow functions ---

async def process_pet_search_request(entity):
    """
    Workflow for pet_search_request entity.
    Set initial status if missing.
    """
    if "status" not in entity:
        entity["status"] = "processing"
    # Placeholder for async processing tasks related to search
    return entity


async def process_pet_detail(entity):
    """
    Workflow for pet_detail entity.
    Enrich pet detail by fetching data from external API.
    """
    if entity.get("status") == "completed" or entity.get("status") == "failed":
        return entity

    pet_id = entity.get("id")
    if not pet_id:
        logger.warning("pet_detail entity missing 'id'")
        entity["status"] = "failed"
        entity["data"] = None
        return entity

    entity["status"] = "processing"  # mark as processing

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"https://petstore.swagger.io/v2/pet/{pet_id}")
            resp.raise_for_status()
            pet = resp.json()

        name = pet.get("name", "Mysterious Pet")
        category = pet.get("category", {}).get("name", "Unknown Category")
        status = pet.get("status", "unknown")
        fun_description = f"{name} is a wonderful {category.lower()} currently {status} and waiting for a loving home! 63b"

        enriched = {
            "id": pet_id,
            "name": name,
            "category": category,
            "status": status,
            "funDescription": fun_description,
        }

        entity["status"] = "completed"
        entity["data"] = enriched

    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        logger.warning(f"HTTP error fetching pet_detail for id {pet_id}: {e}")
        entity["status"] = "failed"
        entity["data"] = None
    except Exception as e:
        logger.exception(f"Unexpected error enriching pet_detail entity with id {pet_id}: {e}")
        entity["status"] = "failed"
        entity["data"] = None

    return entity


@dataclass
class PetSearchRequest:
    status: str
    category: Optional[str] = None

@dataclass
class PetDetailsRequest:
    petIds: List[str]


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
            entity=search_data
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

    async def get_pet_detail_entity(pet_id: str):
        try:
            entity = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="pet_detail",
                entity_version=ENTITY_VERSION,
                technical_id=pet_id
            )
            if entity is None:
                new_entity = {"id": pet_id}
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="pet_detail",
                    entity_version=ENTITY_VERSION,
                    entity=new_entity
                )
                entity = await entity_service.get_item(
                    token=cyoda_auth_service,
                    entity_model="pet_detail",
                    entity_version=ENTITY_VERSION,
                    technical_id=pet_id
                )
            elif entity.get("status") not in ("completed", "failed"):
                # Trigger re-processing if status is neither completed nor failed
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="pet_detail",
                    entity_version=ENTITY_VERSION,
                    entity=entity
                )
                entity = await entity_service.get_item(
                    token=cyoda_auth_service,
                    entity_model="pet_detail",
                    entity_version=ENTITY_VERSION,
                    technical_id=pet_id
                )
            return entity
        except Exception as e:
            logger.exception(f"Failed to get or create pet_detail for id {pet_id}: {e}")
            return None

    tasks = [get_pet_detail_entity(pid) for pid in pet_ids]
    entities = await asyncio.gather(*tasks)

    for ent in entities:
        if ent and ent.get("status") == "completed" and ent.get("data"):
            pets_response.append(ent["data"])
        else:
            logger.warning(f"Pet detail entity incomplete or failed: {ent}")

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