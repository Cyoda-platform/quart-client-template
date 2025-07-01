from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
import uuid

from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring
import httpx

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

app = Quart(__name__)
QuartSchema(app)

@dataclass
class SearchRequest:
    type: str = None
    status: str = None

@dataclass
class DetailRequest:
    petId: int

# Entity models for caching processed results
PET_CACHE_MODEL = "pet_cache"
PET_DETAIL_CACHE_MODEL = "pet_detail_cache"

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

def generate_id() -> str:
    return str(uuid.uuid4())

async def fetch_pets_from_petstore(type_: str = None, status: str = None) -> list:
    query_params = {}
    # Always default to 'available' if no status provided
    query_params["status"] = status if status else "available"
    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=query_params, timeout=10)
            response.raise_for_status()
            pets = response.json()
            if type_:
                return [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == type_.lower()]
            return pets
        except Exception as e:
            logger.exception(f"Failed fetching pets from Petstore: {e}")
            return []

async def fetch_pet_detail_from_petstore(pet_id: int) -> dict:
    url = f"{PETSTORE_BASE_URL}/pet/{pet_id}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.exception(f"Failed fetching pet detail for id {pet_id}: {e}")
            return {}

# Workflow function for 'pet' entity
async def process_pet(entity: dict):
    # Generate searchId if missing
    search_id = entity.get("searchId") or generate_id()
    entity["searchId"] = search_id
    entity["status"] = "pending"
    entity["createdAt"] = datetime.utcnow().isoformat()
    entity["updatedAt"] = entity["createdAt"]
    # Create cache entity for search results
    cache_entity = {
        "searchId": search_id,
        "status": "pending",
        "results": [],
        "createdAt": entity["createdAt"],
        "updatedAt": entity["createdAt"]
    }
    # Add cache entity (different model)
    await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model=PET_CACHE_MODEL,
        entity_version=ENTITY_VERSION,
        entity=cache_entity
    )
    # Fire and forget async task to process search and update cache
    asyncio.create_task(_process_pet_search_task(search_id, entity.get("type"), entity.get("status")))

async def _process_pet_search_task(search_id: str, type_: str, status: str):
    # Defensive: wait a tiny bit to avoid race conditions during persistence (optional)
    await asyncio.sleep(0.1)
    try:
        # Update cache status to processing
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model=PET_CACHE_MODEL,
            entity_version=ENTITY_VERSION,
            technical_id=search_id,
            entity={
                "status": "processing",
                "updatedAt": datetime.utcnow().isoformat()
            }
        )
        pets = await fetch_pets_from_petstore(type_, status)
        results = []
        for pet in pets:
            results.append({
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name") if pet.get("category") else None,
                "status": pet.get("status")
            })
        # Update cache with results and done status
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model=PET_CACHE_MODEL,
            entity_version=ENTITY_VERSION,
            technical_id=search_id,
            entity={
                "results": results,
                "status": "done",
                "updatedAt": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        logger.exception(f"Error processing pet search {search_id}: {e}")
        try:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model=PET_CACHE_MODEL,
                entity_version=ENTITY_VERSION,
                technical_id=search_id,
                entity={"status": "error", "updatedAt": datetime.utcnow().isoformat()}
            )
        except Exception:
            logger.error(f"Failed to update error status for pet search {search_id}")

# Workflow function for 'pet_detail' entity
async def process_pet_detail(entity: dict):
    detail_id = entity.get("detailId") or generate_id()
    entity["detailId"] = detail_id
    entity["status"] = "pending"
    entity["createdAt"] = datetime.utcnow().isoformat()
    entity["updatedAt"] = entity["createdAt"]
    cache_entity = {
        "detailId": detail_id,
        "status": "pending",
        "detail": {},
        "createdAt": entity["createdAt"],
        "updatedAt": entity["createdAt"]
    }
    await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model=PET_DETAIL_CACHE_MODEL,
        entity_version=ENTITY_VERSION,
        entity=cache_entity
    )
    asyncio.create_task(_process_pet_detail_task(detail_id, entity.get("petId")))

async def _process_pet_detail_task(detail_id: str, pet_id: int):
    await asyncio.sleep(0.1)
    try:
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model=PET_DETAIL_CACHE_MODEL,
            entity_version=ENTITY_VERSION,
            technical_id=detail_id,
            entity={
                "status": "processing",
                "updatedAt": datetime.utcnow().isoformat()
            }
        )
        pet = await fetch_pet_detail_from_petstore(pet_id)
        description = pet.get("description") or "No description available."
        pet_processed = {
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name") if pet.get("category") else None,
            "status": pet.get("status"),
            "description": description,
        }
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model=PET_DETAIL_CACHE_MODEL,
            entity_version=ENTITY_VERSION,
            technical_id=detail_id,
            entity={
                "detail": pet_processed,
                "status": "done",
                "updatedAt": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        logger.exception(f"Error processing pet detail {detail_id}: {e}")
        try:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model=PET_DETAIL_CACHE_MODEL,
                entity_version=ENTITY_VERSION,
                technical_id=detail_id,
                entity={"status": "error", "updatedAt": datetime.utcnow().isoformat()}
            )
        except Exception:
            logger.error(f"Failed to update error status for pet detail {detail_id}")

@app.route("/pets/search", methods=["POST"])
@validate_request(SearchRequest)
async def pets_search(data: SearchRequest):
    entity_name = "pet"
    data_dict = data.__dict__
    try:
        id_ = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=data_dict
        )
        return jsonify({"searchId": str(id_)})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add search item"}), 500

@app.route("/pets/search/<string:search_id>", methods=["GET"])
async def get_search_results(search_id):
    try:
        item = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=PET_CACHE_MODEL,
            entity_version=ENTITY_VERSION,
            technical_id=search_id
        )
        if not item:
            return jsonify({"error": "searchId not found"}), 404
        return jsonify({"searchId": search_id, **item})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve search results"}), 500

@app.route("/pets/details", methods=["POST"])
@validate_request(DetailRequest)
async def pets_details(data: DetailRequest):
    entity_name = "pet_detail"
    data_dict = data.__dict__
    try:
        id_ = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=data_dict
        )
        return jsonify({"detailId": str(id_)})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add detail item"}), 500

@app.route("/pets/details/<string:detail_id>", methods=["GET"])
async def get_pet_detail(detail_id):
    try:
        item = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=PET_DETAIL_CACHE_MODEL,
            entity_version=ENTITY_VERSION,
            technical_id=detail_id
        )
        if not item:
            return jsonify({"error": "detailId not found"}), 404
        return jsonify({"detailId": detail_id, **item})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pet detail"}), 500

if __name__ == '__main__':
    import logging as _logging
    _logging.basicConfig(level=_logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
