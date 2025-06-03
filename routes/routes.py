from datetime import timezone, datetime
import logging
from quart import Blueprint, request, abort, jsonify
from quart_schema import validate, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
FINAL_STATES = {'FAILURE', 'SUCCESS', 'CANCELLED', 'CANCELLED_BY_USER', 'UNKNOWN', 'FINISHED'}
PROCESSING_STATE = 'PROCESSING'

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

import asyncio
import httpx
from dataclasses import dataclass
from typing import Optional, List

PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

entity_jobs = {}
entity_jobs_lock = asyncio.Lock()

@dataclass
class PetQuery:
    type: Optional[str]
    status: Optional[str]

@dataclass
class FavoritePet:
    petId: int

async def fetch_pets_from_petstore(
    type_filter: Optional[str] = None, status_filter: Optional[str] = None
) -> List[dict]:
    statuses = [status_filter] if status_filter else ["available"]
    pets: List[dict] = []
    async with httpx.AsyncClient(timeout=10) as client:
        for status in statuses:
            try:
                resp = await client.get(
                    f"{PETSTORE_BASE_URL}/pet/findByStatus", params={"status": status}
                )
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, list):
                    pets.extend(data)
            except httpx.HTTPError as e:
                logger.exception(f"Failed to fetch pets by status '{status}': {e}")
    if type_filter:
        pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == type_filter.lower()]
    return pets

async def trigger_event_workflow(event_type: str, payload: dict):
    job_id = f"{event_type}_{datetime.utcnow().isoformat()}"
    async with entity_jobs_lock:
        entity_jobs[job_id] = {"status": "processing", "requestedAt": datetime.utcnow().isoformat(), "payload": payload}
    logger.info(f"Event triggered: {event_type}, job id: {job_id}")
    asyncio.create_task(process_event_job(job_id))

async def process_event_job(job_id: str):
    try:
        await asyncio.sleep(0.5)
        async with entity_jobs_lock:
            if job_id in entity_jobs:
                entity_jobs[job_id]["status"] = "done"
                logger.info(f"Event job {job_id} done.")
    except Exception as e:
        logger.exception(f"Error processing event job {job_id}: {e}")

async def process_pet(entity: dict) -> dict:
    entity["processedAt"] = datetime.utcnow().isoformat()
    return entity

async def process_favorite_pet(entity: dict) -> dict:
    asyncio.create_task(trigger_event_workflow("pet_favorite", {"petId": entity.get("petId")}))
    return entity

@routes_bp.route("/pets/query", methods=["POST"])
@validate_request(PetQuery)
async def pets_query(data: PetQuery):
    try:
        pets = await fetch_pets_from_petstore(data.type, data.status)
        for pet in pets:
            try:
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="pet",
                    entity_version=ENTITY_VERSION,
                    entity=pet
                )
            except Exception as e:
                logger.exception(f"Failed to add pet to entity_service: {e}")
        await trigger_event_workflow("pet_query", {"type": data.type, "status": data.status, "resultCount": len(pets)})
        return jsonify({"pets": pets})
    except Exception as e:
        logger.exception("Error in /pets/query")
        return jsonify({"error": "Failed to query pets"}), 500

@routes_bp.route("/pets", methods=["GET"])
async def pets_get():
    try:
        pets = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
        )
        return jsonify({"pets": pets})
    except Exception as e:
        logger.exception("Error in /pets GET")
        return jsonify({"error": "Failed to get pets"}), 500

@routes_bp.route("/pets/<string:pet_id>", methods=["GET"])
async def pet_get(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
        )
        if pet is None:
            return jsonify({"error": "Pet not found"}), 404
        return jsonify(pet)
    except Exception as e:
        logger.exception(f"Error in /pets/{pet_id} GET")
        return jsonify({"error": "Failed to get pet"}), 500

@routes_bp.route("/pets/favorite", methods=["POST"])
@validate_request(FavoritePet)
async def pets_favorite(data: FavoritePet):
    try:
        pet_id_str = str(data.petId)
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id_str,
        )
        if pet is None:
            return jsonify({"error": "Pet not found"}), 404
        try:
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model="favorite_pet",
                entity_version=ENTITY_VERSION,
                entity={"petId": pet_id_str}
            )
        except Exception as e:
            logger.exception(f"Failed to add favorite pet: {e}")
            return jsonify({"error": "Failed to mark pet as favorite"}), 500
        return jsonify({"message": "Pet marked as favorite", "petId": pet_id_str})
    except Exception as e:
        logger.exception("Error in /pets/favorite")
        return jsonify({"error": "Failed to mark pet as favorite"}), 500