import asyncio
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

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

@dataclass
class PetSearchFilters:
    type: Optional[str] = None
    status: Optional[str] = None
    breed: Optional[str] = None

@dataclass
class PetDetailsRequest:
    pet_id: str  # changed to string id as required

SEARCH_RESULTS_KEY = "latest_search_results"

@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearchFilters)
async def pets_search(data: PetSearchFilters):
    filters = {k: v for k, v in data.__dict__.items() if v is not None}
    # Use entity_service to add search job as an entity
    entity_name = "pet_search_filters"
    id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model=entity_name,
        entity_version=ENTITY_VERSION,
        entity=filters
    )
    return jsonify({"jobId": id, "status": "processing"}), 202

@app.route("/pets/results", methods=["GET"])
async def pets_results():
    entity_name = "pet_search_filters"
    try:
        # retrieve all search filter entities
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=entity_name,
            entity_version=ENTITY_VERSION,
        )
        # We assume only the latest search is relevant; if multiple, take last
        if not items:
            return jsonify({"pets": []})
        latest_filters = items[-1]

        # Compose condition for pets with status and type filters
        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": []
            }
        }
        # Add conditions as per filters
        if "status" in latest_filters and latest_filters["status"]:
            condition["cyoda"]["conditions"].append({
                "jsonPath": "$.status",
                "operatorType": "EQUALS",
                "value": latest_filters["status"],
                "type": "simple"
            })
        if "type" in latest_filters and latest_filters["type"]:
            condition["cyoda"]["conditions"].append({
                "jsonPath": "$.category.name",
                "operatorType": "IEQUALS",
                "value": latest_filters["type"],
                "type": "simple"
            })
        if "breed" in latest_filters and latest_filters["breed"]:
            condition["cyoda"]["conditions"].append({
                "jsonPath": "$.name",
                "operatorType": "IEQUALS",
                "value": latest_filters["breed"],
                "type": "simple"
            })

        # Retrieve pets matching the condition
        pets = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            condition=condition
        )
        response_pets = []
        for pet in pets:
            response_pets.append({
                "id": pet.get("id"),
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name"),
                "breed": pet.get("name"),
                "status": pet.get("status"),
                "photoUrls": pet.get("photoUrls", [])
            })
        return jsonify({"pets": response_pets})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve results"}), 500

@app.route("/pets/details", methods=["POST"])
@validate_request(PetDetailsRequest)
async def pets_details(data: PetDetailsRequest):
    pet_id = str(data.pet_id)  # ensure string id
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
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pet details"}), 500

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)