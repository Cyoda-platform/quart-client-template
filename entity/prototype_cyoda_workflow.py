from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import asyncio
import logging
from datetime import datetime
import uuid

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"
RANDOM_PET_FACTS_URL = "https://some-random-api.ml/facts/cat"

@dataclass
class PetAction:
    action: str
    pet: Optional[Dict[str, Any]]

@dataclass
class PetSearch:
    category: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None

async def fetch_pet_from_petstore(pet_id: str) -> Optional[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{PETSTORE_BASE_URL}/pet/{pet_id}")
            r.raise_for_status()
            pet = r.json()
            return pet
        except httpx.HTTPStatusError as e:
            logger.warning(f"Petstore API returned error for pet_id={pet_id}: {e}")
            return None
        except Exception as e:
            logger.exception(e)
            return None

async def search_pets_from_petstore(
    category: Optional[str], status: Optional[str], tags: Optional[List[str]]
) -> List[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        try:
            url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
            params = {}
            if status:
                params["status"] = status
            else:
                params["status"] = "available,pending,sold"

            r = await client.get(url, params=params)
            r.raise_for_status()
            pets = r.json()

            def matches(p):
                if category and (p.get("category", {}).get("name", "").lower() != category.lower()):
                    return False
                if tags:
                    pet_tags = [t["name"].lower() for t in p.get("tags", [])]
                    if not all(tag.lower() in pet_tags for tag in tags):
                        return False
                return True

            filtered = [p for p in pets if matches(p)]
            return filtered
        except Exception as e:
            logger.exception(e)
            return []

async def get_random_pet_fact() -> str:
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(RANDOM_PET_FACTS_URL)
            r.raise_for_status()
            data = r.json()
            fact = data.get("fact")
            if not fact:
                fact = "Cats are mysterious and wonderful creatures!"
            return fact
        except Exception as e:
            logger.warning(f"Failed to fetch random pet fact: {e}")
            return "Cats are mysterious and wonderful creatures!"

# Workflow function for 'pet' entity model - moves all async processing here for add/update actions.
async def process_pet(entity: Dict[str, Any]) -> Dict[str, Any]:
    """
    Workflow function applied to pet entity before persistence.
    Handles async tasks such as enrichment, validation, supplement data fetching.
    """
    action = entity.get("action")

    # Remove 'action' before persistence - model should not store it
    if "action" in entity:
        del entity["action"]

    # Add processedAt timestamp always
    entity["processedAt"] = datetime.utcnow().isoformat()

    if action == "add":
        # Generate ID if missing
        if not entity.get("id"):
            entity["id"] = str(uuid.uuid4())

        # Example enrichment: fetch random pet fact asynchronously and add as 'funFact' attribute
        try:
            fact = await get_random_pet_fact()
            entity["funFact"] = fact
        except Exception as e:
            logger.warning(f"Failed to fetch random pet fact: {e}")

        # Optionally, fetch additional pet data from petstore and merge (simulate enrichment)
        petstore_data = await fetch_pet_from_petstore(entity["id"])
        if petstore_data:
            # Merge or add fields from petstore data which do not override existing keys
            for k, v in petstore_data.items():
                if k not in entity:
                    entity[k] = v

    elif action == "update":
        pet_id = entity.get("id")
        if pet_id:
            # Optionally enrich updated pet with latest petstore data
            petstore_data = await fetch_pet_from_petstore(pet_id)
            if petstore_data:
                for k, v in petstore_data.items():
                    # Update fields only if not present in update entity to avoid overwriting
                    if k not in entity:
                        entity[k] = v
        # else: no enrichment possible without id

    # For other actions or no action: just add processedAt timestamp

    return entity

# POST /pets - handle add or update pet
@app.route("/pets", methods=["POST"])
@validate_request(PetAction)
async def pets_post(data: PetAction):
    pet_entity = data.pet or {}
    pet_entity["action"] = data.action

    # Since we want to persist pet entity with workflow, just add or update
    if data.action == "add":
        try:
            id = await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                entity=pet_entity,
                workflow=process_pet,
            )
            return jsonify({"id": id}), 201
        except Exception as e:
            logger.exception(e)
            return jsonify({"error": "Failed to add pet"}), 500

    elif data.action == "update":
        pet_id = pet_entity.get("id")
        if not pet_id:
            return jsonify({"error": "Pet id required for update"}), 400
        try:
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                entity=pet_entity,
                technical_id=pet_id,
                meta={},
                workflow=process_pet,
            )
            updated_pet = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                technical_id=pet_id,
            )
            return jsonify(updated_pet)
        except Exception as e:
            logger.exception(e)
            return jsonify({"error": "Failed to update pet"}), 500

    else:
        return jsonify({"error": "Unsupported action"}), 400

# GET /pets/<pet_id> - fetch pet, no persistence, no workflow
@app.route("/pets/<pet_id>", methods=["GET"])
async def get_pet(pet_id):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
        )
        if not pet:
            return jsonify({"error": "Pet not found"}), 404
        return jsonify(pet)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pet"}), 500

# POST /pets/search - search pets from petstore (no persistence, no workflow)
@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearch)
async def search_pets(data: PetSearch):
    pets = await search_pets_from_petstore(data.category, data.status, data.tags)
    return jsonify({"pets": pets})

# GET /pets/random-fact - fetch random fact (no persistence, no workflow)
@app.route("/pets/random-fact", methods=["GET"])
async def random_fact():
    fact = await get_random_pet_fact()
    return jsonify({"fact": fact})

if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)