import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx
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
class PetSearch:
    type: Optional[str] = None
    status: Optional[str] = None

async def process_pet(entity):
    """
    Workflow function applied to the 'pet' entity asynchronously before persistence.
    Modify the entity as needed. For example, add a timestamp or default values.
    Cannot add/update/delete 'pet' entity inside this function to avoid recursion.
    """
    entity["processed_at"] = datetime.utcnow().isoformat()
    # Additional enrichment or side effects can be added here safely
    return entity

async def process_petsearch(entity):
    """
    Workflow function applied to the 'petsearch' entity asynchronously before persistence.
    Performs the Petstore API call, filters by type/status, and saves pets asynchronously.
    """
    pet_type = entity.get("type")
    status = entity.get("status") or "available"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            params = {"status": status}
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params=params)
            resp.raise_for_status()
            pets_raw = resp.json()

        if pet_type:
            pets_filtered = [p for p in pets_raw if p.get("category") and p["category"].get("name", "").lower() == pet_type.lower()]
        else:
            pets_filtered = pets_raw

        # Save each pet entity via entity_service.add_item with workflow=process_pet
        async def save_pet(pet):
            pet_data = {
                "id": str(pet.get("id")),
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name", None),
                "status": pet.get("status"),
                "photoUrls": pet.get("photoUrls", []),
            }
            try:
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="pet",
                    entity_version=ENTITY_VERSION,
                    entity=pet_data,
                    workflow=process_pet,
                )
            except Exception as e:
                logger.exception(f"Failed to save pet {pet_data.get('id')}: {e}")

        # Limit concurrency to avoid overwhelming the service
        sem = asyncio.Semaphore(10)

        async def sem_save_pet(p):
            async with sem:
                await save_pet(p)

        await asyncio.gather(*(sem_save_pet(p) for p in pets_filtered))

    except Exception as e:
        logger.exception(f"Failed to process petsearch entity: {e}")

    # Mark petsearch entity processed timestamp
    entity["processed_at"] = datetime.utcnow().isoformat()
    return entity


@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearch)
async def pets_search(data: PetSearch):
    """
    POST /pets/search
    Accepts optional filters: type, status
    Creates a 'petsearch' entity; actual search and persistence handled asynchronously in workflow.
    """
    try:
        search_data = {
            "type": data.type,
            "status": data.status,
        }
        search_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="petsearch",
            entity_version=ENTITY_VERSION,
            entity=search_data,
            workflow=process_petsearch,
        )
        return jsonify({"search_id": search_id, "message": "Pet search request accepted and processing."})

    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to initiate pet search"}), 500


@app.route("/pets/fun-fact", methods=["POST"])
async def pets_fun_fact():
    import random
    fact = random.choice(FUN_PET_FACTS)
    return jsonify({"fact": fact})

@app.route("/pets", methods=["GET"])
async def get_pets():
    try:
        pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
        )
        return jsonify({"pets": pets})
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pets"}), 500

@app.route("/pets/<string:pet_id>", methods=["GET"])
async def get_pet_by_id(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
        )
        if pet is None:
            return jsonify({"error": f"Pet with id {pet_id} not found."}), 404
        return jsonify(pet)
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pet"}), 500


if __name__ == '__main__':
    import sys
    import os

    PETSTORE_BASE_URL = os.getenv("PETSTORE_BASE_URL", "https://petstore.swagger.io/v2")
    FUN_PET_FACTS = [
        "Cats sleep 70% of their lives.",
        "Dogs have three eyelids.",
        "Goldfish have a memory span of three months.",
        "Rabbits can't vomit.",
    ]

    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)