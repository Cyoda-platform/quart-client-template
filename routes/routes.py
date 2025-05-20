import asyncio
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

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

@dataclass
class PetSearchFilters:
    type: Optional[str] = None
    status: Optional[str] = None
    breed: Optional[str] = None

@dataclass
class PetDetailsRequest:
    pet_id: str  # id as string

async def process_pet_search_filters(entity_data):
    """
    Workflow function called before persisting pet_search_filters entity.
    This function performs the pet search based on filters and stores results
    in a new pet_search_results entity asynchronously.
    """
    entity_data["processed_at"] = datetime.utcnow().isoformat()

    conditions = []

    if entity_data.get("status"):
        conditions.append({
            "jsonPath": "$.status",
            "operatorType": "EQUALS",
            "value": entity_data["status"],
            "type": "simple"
        })

    if entity_data.get("type"):
        conditions.append({
            "jsonPath": "$.category.name",
            "operatorType": "IEQUALS",
            "value": entity_data["type"],
            "type": "simple"
        })

    if entity_data.get("breed"):
        conditions.append({
            "jsonPath": "$.name",
            "operatorType": "IEQUALS",
            "value": entity_data["breed"],
            "type": "simple"
        })

    condition = {
        "cyoda": {
            "type": "group",
            "operator": "AND",
            "conditions": conditions
        }
    }

    try:
        pets = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            condition=condition
        )
    except Exception as e:
        logger.error(f"Error fetching pets in workflow: {e}")
        pets = []

    pet_results = []
    for pet in pets:
        pet_results.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "type": pet.get("category", {}).get("name"),
            "breed": pet.get("name"),
            "status": pet.get("status"),
            "photoUrls": pet.get("photoUrls", [])
        })

    try:
        # Attempt to get the entity id if available, else None
        search_filter_id = entity_data.get("id")
        # If id is None, add a timestamp-based temporary id
        if not search_filter_id:
            search_filter_id = f"temp-{datetime.utcnow().timestamp()}"

        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet_search_results",
            entity_version=ENTITY_VERSION,
            entity={
                "search_filter_id": search_filter_id,
                "timestamp": datetime.utcnow().isoformat(),
                "results": pet_results
            },
            workflow=None  # No workflow on results entity to prevent recursion
        )
    except Exception as e:
        logger.error(f"Failed to save pet_search_results entity: {e}")

@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearchFilters)
async def pets_search(data: PetSearchFilters):
    filters = {k: v for k, v in data.__dict__.items() if v is not None}
    entity_name = "pet_search_filters"
    try:
        id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
            entity=filters,
            workflow=None
        )
        return jsonify({"jobId": id, "status": "processing"}), 202
    except Exception as e:
        logger.exception(f"Failed to add pet_search_filters entity: {e}")
        return jsonify({"error": "Failed to initiate pet search"}), 500

@app.route("/pets/results", methods=["GET"])
async def pets_results():
    try:
        results_entities = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet_search_results",
            entity_version=ENTITY_VERSION,
        )
        if not results_entities:
            return jsonify({"pets": []})

        # Safely get latest results by timestamp, handle missing timestamps
        def safe_timestamp(e):
            ts = e.get("timestamp")
            if not ts:
                return ""
            return ts

        latest_results_entity = max(results_entities, key=safe_timestamp)
        pets = latest_results_entity.get("results", [])
        return jsonify({"pets": pets})

    except Exception as e:
        logger.exception(f"Failed to retrieve pet search results: {e}")
        return jsonify({"error": "Failed to retrieve results"}), 500

@app.route("/pets/details", methods=["POST"])
@validate_request(PetDetailsRequest)
async def pets_details(data: PetDetailsRequest):
    pet_id = str(data.pet_id)
    try:
        pet_details = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
        if not pet_details:
            return jsonify({"error": "Pet not found"}), 404

        response = {
            "id": pet_details.get("id"),
            "name": pet_details.get("name"),
            "type": pet_details.get("category", {}).get("name"),
            "breed": pet_details.get("name"),
            "status": pet_details.get("status"),
            "photoUrls": pet_details.get("photoUrls", []),
            "description": pet_details.get("tags", [{}])[0].get("name", "")
        }
        return jsonify(response)
    except Exception as e:
        logger.exception(f"Failed to retrieve pet details: {e}")
        return jsonify({"error": "Failed to retrieve pet details"}), 500

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)