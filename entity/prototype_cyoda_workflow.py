from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
import uuid

from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request
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

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

def generate_id() -> str:
    return str(uuid.uuid4())

async def fetch_pets_from_petstore(status: str):
    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
    params = {"status": status}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()

async def fetch_pet_detail_from_petstore(pet_id: int):
    url = f"{PETSTORE_BASE_URL}/pet/{pet_id}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=10)
        response.raise_for_status()
        return response.json()

async def process_pet(entity: dict):
    """
    Workflow for pet search entity:
    - Generate searchId
    - Store it in entity to persist
    - Add a secondary entity 'pet_search_result' to hold results & status
    - Fire off background search task that updates this secondary entity
    """
    search_id = generate_id()
    entity["searchId"] = search_id

    search_result_entity = {
        "searchId": search_id,
        "status": "queued",
        "results": [],
        "createdAt": datetime.utcnow().isoformat() + "Z"
    }

    # Add 'pet_search_result' entity (different entity_model)
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet_search_result",
            entity_version=ENTITY_VERSION,
            entity=search_result_entity,
        )
    except Exception as e:
        logger.exception(f"Failed to add pet_search_result entity for searchId={search_id}: {e}")

    # Fire and forget background task to fetch pets and update pet_search_result entity
    asyncio.create_task(_background_process_pet_search(search_id, entity.get("type"), entity.get("status")))

    return entity

async def _background_process_pet_search(search_id: str, type_: str = None, status: str = None):
    try:
        status_query = status if status else "available"
        pets = await fetch_pets_from_petstore(status_query)

        if type_:
            pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == type_.lower()]

        results = []
        for pet in pets:
            results.append({
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name") if pet.get("category") else None,
                "status": pet.get("status")
            })

        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="pet_search_result",
            entity_version=ENTITY_VERSION,
            technical_id=search_id,
            entity={
                "status": "done",
                "results": results,
                "updatedAt": datetime.utcnow().isoformat() + "Z"
            }
        )
    except Exception as e:
        logger.exception(f"Error in background pet search processing for searchId={search_id}: {e}")
        try:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="pet_search_result",
                entity_version=ENTITY_VERSION,
                technical_id=search_id,
                entity={"status": "error", "updatedAt": datetime.utcnow().isoformat() + "Z"}
            )
        except Exception:
            pass

async def process_pet_detail(entity: dict):
    """
    Workflow for pet detail entity:
    - Generate detailId
    - Store in entity to persist
    - Add secondary entity 'pet_detail_result' to hold detail & status
    - Fire off background detail fetch task that updates the secondary entity
    """
    detail_id = generate_id()
    entity["detailId"] = detail_id
    pet_id = entity.get("petId")

    detail_result_entity = {
        "detailId": detail_id,
        "status": "queued",
        "detail": {},
        "createdAt": datetime.utcnow().isoformat() + "Z"
    }

    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet_detail_result",
            entity_version=ENTITY_VERSION,
            entity=detail_result_entity,
        )
    except Exception as e:
        logger.exception(f"Failed to add pet_detail_result entity for detailId={detail_id}: {e}")

    asyncio.create_task(_background_process_pet_detail(detail_id, pet_id))

    return entity

async def _background_process_pet_detail(detail_id: str, pet_id: int):
    try:
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
            entity_model="pet_detail_result",
            entity_version=ENTITY_VERSION,
            technical_id=detail_id,
            entity={
                "status": "done",
                "detail": pet_processed,
                "updatedAt": datetime.utcnow().isoformat() + "Z"
            }
        )
    except Exception as e:
        logger.exception(f"Error in background pet detail processing for detailId={detail_id}: {e}")
        try:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="pet_detail_result",
                entity_version=ENTITY_VERSION,
                technical_id=detail_id,
                entity={"status": "error", "updatedAt": datetime.utcnow().isoformat() + "Z"}
            )
        except Exception:
            pass

@app.route("/pets/search", methods=["POST"])
@validate_request(SearchRequest)
async def pets_search(data: SearchRequest):
    entity_name = "pet"
    data_dict = data.__dict__
    try:
        # add_item returns technical_id but searchId is inside entity dict
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=data_dict,
            workflow=process_pet
        )
        return jsonify({"searchId": str(data_dict.get("searchId"))})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add search item"}), 500

@app.route("/pets/search/<string:search_id>", methods=["GET"])
async def get_search_results(search_id):
    entity_name = "pet_search_result"
    try:
        item = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            technical_id=search_id,
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
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=data_dict,
            workflow=process_pet_detail
        )
        return jsonify({"detailId": str(data_dict.get("detailId"))})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add detail item"}), 500

@app.route("/pets/details/<string:detail_id>", methods=["GET"])
async def get_pet_detail(detail_id):
    entity_name = "pet_detail_result"
    try:
        item = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            technical_id=detail_id,
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