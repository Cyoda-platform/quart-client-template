import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List, Optional

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

@dataclass
class FetchPetsRequest:
    type: Optional[str]
    status: Optional[str]

@dataclass
class AgeRange:
    min: int
    max: int

@dataclass
class MatchPetsRequest:
    preferredType: str
    ageRange: AgeRange
    status: str

PET_ENTITY_NAME = "pet"

PETSTORE_API_BASE = "https://petstore.swagger.io/v2"

async def fetch_pets_from_petstore(
    pet_type: Optional[str] = None, status: Optional[str] = None
) -> List[Dict[str, Any]]:
    url = f"{PETSTORE_API_BASE}/pet/findByStatus"
    params = {"status": status or "available"}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
            if pet_type:
                pet_type_lower = pet_type.lower()
                filtered = []
                for pet in pets:
                    category = pet.get("category") or {}
                    cat_name = category.get("name", "").lower()
                    if pet_type_lower == "other":
                        if cat_name not in ("cat", "dog"):
                            filtered.append(pet)
                    elif cat_name == pet_type_lower:
                        filtered.append(pet)
                pets = filtered
            return pets
        except Exception as e:
            logger.exception(f"Failed to fetch pets: {e}")
            return []

@app.route("/pets/fetch", methods=["POST"])
@validate_request(FetchPetsRequest)  # workaround: validation last for POST due to quart-schema issue
async def pets_fetch(data: FetchPetsRequest):
    try:
        pets = await fetch_pets_from_petstore(data.type, data.status)
        # Add pets to entity service asynchronously - add_item returns id, no bulk add, so add one by one
        for pet in pets:
            try:
                # Convert id to string as technical_id is string everywhere
                pet_id = str(pet.get("id")) if pet.get("id") is not None else None
                if pet_id is None:
                    continue  # skip if no id
                # Add pet to entity_service; ignoring returned id here as pet already has id
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model=PET_ENTITY_NAME,
                    entity_version=ENTITY_VERSION,
                    entity=pet
                )
            except Exception as e:
                logger.exception(f"Failed to add pet {pet_id} to entity_service: {e}")
        return jsonify({
            "message": "Pets data fetched and stored successfully",
            "fetchedCount": len(pets),
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to fetch pets"}), 500

async def find_pet_matches(
    preferred_type: str, age_min: int, age_max: int, status: str
) -> List[Dict[str, Any]]:
    try:
        # Build condition for entity_service.get_items_by_condition
        conditions = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": [
                    {
                        "jsonPath": "$.status",
                        "operatorType": "EQUALS",
                        "value": status,
                        "type": "simple"
                    }
                ]
            }
        }
        # Retrieve matching pets by condition
        pets = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            condition=conditions
        )
        results = []
        for pet in pets:
            category = pet.get("category") or {}
            pet_type = category.get("name", "").lower() or "other"
            if preferred_type.lower() != pet_type and preferred_type.lower() != "other":
                continue
            # Mock age as before
            age = 3  # TODO: mock age, Petstore API has no age field
            if age_min <= age <= age_max:
                results.append({
                    "id": pet.get("id"),
                    "name": pet.get("name"),
                    "type": pet_type,
                    "age": age,
                    "status": pet.get("status", "available"),
                })
        return results
    except Exception as e:
        logger.exception(f"Failed to find pet matches: {e}")
        return []

@app.route("/pets/match", methods=["POST"])
@validate_request(MatchPetsRequest)  # workaround: validation last for POST due to quart-schema issue
async def pets_match(data: MatchPetsRequest):
    try:
        matches = await find_pet_matches(
            data.preferredType, data.ageRange.min, data.ageRange.max, data.status
        )
        return jsonify({"matches": matches})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to find pet matches"}), 500

@app.route("/pets", methods=["GET"])
async def pets_list():
    try:
        pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        return jsonify(pets)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pets"}), 500

@app.route("/pets/<string:pet_id>", methods=["GET"])
async def pet_details(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
        if not pet:
            return jsonify({"error": "Pet not found"}), 404
        pet_detail = pet.copy()
        pet_detail["description"] = pet_detail.get(
            "description", "Playful pet who loves attention."
        )  # TODO: mock description, Petstore API has no description field
        return jsonify(pet_detail)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pet details"}), 500

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)