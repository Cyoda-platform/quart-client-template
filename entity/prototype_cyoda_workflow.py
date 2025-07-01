Certainly! I've updated the code to add the `workflow` parameter to `entity_service.add_item` calls, and implemented the required workflow functions with the appropriate `process_` prefix and underscore-lowercase entity names (`process_pet` and `process_pet_detail`). These functions will be passed as the `workflow` argument and applied to the entity data asynchronously before persistence.

Here is the complete updated code:

```python
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

app.search_cache = {}
app.detail_cache = {}

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

def generate_id() -> str:
    return str(uuid.uuid4())

async def fetch_pets_from_petstore(type_: str = None, status: str = None) -> list:
    query_params = {}
    if status:
        query_params["status"] = status
    if not status:
        query_params["status"] = "available"
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
async def process_pet(entity_data: dict):
    # entity_data is the dict passed to add_item
    # Generate a unique searchId and initialize cache
    search_id = generate_id()
    app.search_cache[search_id] = {
        "status": "queued",
        "results": []
    }
    # Start background processing asynchronously, do not await here
    asyncio.create_task(process_search(search_id, entity_data.get("type"), entity_data.get("status")))
    # Add the generated searchId into the entity_data so it can be persisted with it
    entity_data["searchId"] = search_id
    return entity_data

# Workflow function for 'pet_detail' entity
async def process_pet_detail(entity_data: dict):
    # entity_data is the dict passed to add_item
    detail_id = generate_id()
    app.detail_cache[detail_id] = {
        "status": "queued",
        "detail": {}
    }
    pet_id = entity_data.get("petId")
    # Start background processing asynchronously, do not await here
    asyncio.create_task(process_detail(detail_id, pet_id))
    # Add the generated detailId into the entity_data so it can be persisted with it
    entity_data["detailId"] = detail_id
    return entity_data

async def process_search(search_id: str, type_: str, status: str):
    app.search_cache[search_id]["status"] = "processing"
    try:
        pets = await fetch_pets_from_petstore(type_, status)
        results = []
        for pet in pets:
            results.append({
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name") if pet.get("category") else None,
                "status": pet.get("status")
            })
        app.search_cache[search_id]["results"] = results
        app.search_cache[search_id]["status"] = "done"
    except Exception as e:
        logger.exception(f"Error processing search {search_id}: {e}")
        app.search_cache[search_id]["status"] = "error"

async def process_detail(detail_id: str, pet_id: int):
    app.detail_cache[detail_id]["status"] = "processing"
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
        app.detail_cache[detail_id]["detail"] = pet_processed
        app.detail_cache[detail_id]["status"] = "done"
    except Exception as e:
        logger.exception(f"Error processing detail {detail_id}: {e}")
        app.detail_cache[detail_id]["status"] = "error"

@app.route("/pets/search", methods=["POST"])
@validate_request(SearchRequest)
async def pets_search(data: SearchRequest):
    entity_name = "pet"  # entity name always underscore lowercase
    data_dict = data.__dict__
    try:
        id_ = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=data_dict,
            workflow=process_pet  # Added workflow function here
        )
        return jsonify({"searchId": str(id_)})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add search item"}), 500

@app.route("/pets/search/<string:search_id>", methods=["GET"])
async def get_search_results(search_id):
    entity_name = "pet"
    try:
        item = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            technical_id=search_id
        )
        if not item:
            return jsonify({"error": "searchId not found"}), 404
        return jsonify({"searchId": search_id, "results": item})
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
            entity=data_dict,
            workflow=process_pet_detail  # Added workflow function here
        )
        return jsonify({"detailId": str(id_)})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add detail item"}), 500

@app.route("/pets/details/<string:detail_id>", methods=["GET"])
async def get_pet_detail(detail_id):
    entity_name = "pet_detail"
    try:
        item = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
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
```

### Explanation of changes:
- Added `process_pet` and `process_pet_detail` async functions as workflows.
- These functions mutate the entity data by adding the generated IDs (`searchId` or `detailId`) and start background processing tasks.
- In the calls to `entity_service.add_item` for `"pet"` and `"pet_detail"` entities, the `workflow` argument is now provided with the respective workflow function.
- This matches the new expected signature of `add_item` and ensures the entity is processed before persistence.

Let me know if you need any further adjustments!