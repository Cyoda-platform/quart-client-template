from datetime import timezone, datetime
import logging
from quart import Blueprint, request, abort, jsonify
from quart_schema import validate, validate_querystring, tag, operation_id
from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
FINAL_STATES = {'FAILURE', 'SUCCESS', 'CANCELLED', 'CANCELLED_BY_USER', 'UNKNOWN', 'FINISHED'}
PROCESSING_STATE = 'PROCESSING'

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

PET_ENTITY_NAME = "pets"
PETSTORE_BASE_URL = "https://petstore.swagger.io/v2"

import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
import httpx

@dataclass
class FetchPetsRequest:
    status: Optional[str] = None
    category: Optional[str] = None

@dataclass
class GetPetsQuery:
    status: Optional[str] = None
    category: Optional[str] = None
    limit: int = 20
    offset: int = 0

@dataclass
class AdoptPetRequest:
    petid: str

async def process_pets(entity: Dict) -> Dict:
    if "status" in entity and isinstance(entity["status"], str):
        entity["status"] = entity["status"].lower()
    entity["processed_at"] = datetime.utcnow().isoformat()
    if "name" in entity and isinstance(entity["name"], str):
        entity["name_length"] = len(entity["name"])
    return entity

async def fetch_pets_from_petstore(status: Optional[str], category: Optional[str]) -> List[Dict]:
    try:
        async with httpx.AsyncClient() as client:
            query_status = status if status else "available,pending,sold"
            url = f"{PETSTORE_BASE_URL}/pet/findByStatus"
            response = await client.get(url, params={"status": query_status})
            response.raise_for_status()
            pets = response.json()
            if category:
                cat_lower = category.lower()
                pets = [
                    pet for pet in pets
                    if pet.get("category", {}).get("name", "").lower() == cat_lower
                ]
            return pets
    except Exception as e:
        logger.exception(f"Failed to fetch pets from Petstore API: {e}")
        return []

async def store_pets(pets: List[Dict]):
    for pet in pets:
        pet_id = pet.get("id")
        if pet_id is None:
            continue
        technical_id = str(pet_id)
        try:
            existing_pet = await entity_service.get_item(
                token=cyoda_auth_service,
                entity_model=PET_ENTITY_NAME,
                entity_version=ENTITY_VERSION,
                technical_id=technical_id
            )
        except Exception:
            existing_pet = None
        if existing_pet is None:
            data = {
                "id": technical_id,
                "name": pet.get("name", ""),
                "category": pet.get("category", {}).get("name", ""),
                "status": pet.get("status", ""),
            }
            try:
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model=PET_ENTITY_NAME,
                    entity_version=ENTITY_VERSION,
                    entity=data
                )
            except Exception as e:
                logger.exception(f"Failed to store pet id {technical_id}: {e}")

@routes_bp.route("/pets/fetch", methods=["POST"])
@validate(FetchPetsRequest)
async def fetch_pets(data: FetchPetsRequest):
    requested_at = datetime.utcnow().isoformat()
    logger.info(f"Fetch request at {requested_at} with status={data.status} category={data.category}")

    async def async_fetch_and_store():
        pets = await fetch_pets_from_petstore(data.status, data.category)
        await store_pets(pets)
        logger.info(f"Fetched and stored {len(pets)} pets")

    asyncio.create_task(async_fetch_and_store())
    return jsonify({"message": "Pets data fetch started asynchronously.", "requestedAt": requested_at}), 202

@routes_bp.route("/pets", methods=["GET"])
@validate_querystring(GetPetsQuery)
async def get_pets():
    try:
        status = request.args.get("status")
        category = request.args.get("category")
        limit = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))

        conditions = {"cyoda": {"type": "group", "operator": "AND", "conditions": []}}

        if status:
            conditions["cyoda"]["conditions"].append({
                "jsonPath": "$.status",
                "operatorType": "EQUALS",
                "value": status.lower(),
                "type": "simple"
            })
        if category:
            conditions["cyoda"]["conditions"].append({
                "jsonPath": "$.category",
                "operatorType": "EQUALS",
                "value": category.lower(),
                "type": "simple"
            })

        if conditions["cyoda"]["conditions"]:
            all_pets = await entity_service.get_items_by_condition(
                token=cyoda_auth_service,
                entity_model=PET_ENTITY_NAME,
                entity_version=ENTITY_VERSION,
                condition=conditions
            )
        else:
            all_pets = await entity_service.get_items(
                token=cyoda_auth_service,
                entity_model=PET_ENTITY_NAME,
                entity_version=ENTITY_VERSION
            )

        pets_list = all_pets or []
        total = len(pets_list)
        page = pets_list[offset: offset + limit]

        return jsonify({"pets": page, "total": total, "limit": limit, "offset": offset})
    except Exception as e:
        logger.exception(f"Failed to retrieve pets: {e}")
        return jsonify({"error": "Failed to retrieve pets"}), 500

@routes_bp.route("/pets/adopt", methods=["POST"])
@validate(AdoptPetRequest)
async def adopt(data: AdoptPetRequest):
    pet_id = data.petid
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
        if not pet:
            return jsonify({"error": f"Pet with id {pet_id} not found"}), 404

        pet["status"] = "sold"

        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model=PET_ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=pet,
            technical_id=pet_id,
            meta={}
        )
        return jsonify({"message": f"Pet {pet_id} adopted successfully.", "pet": pet})
    except Exception as e:
        logger.exception(f"Failed to adopt pet id {pet_id}: {e}")
        return jsonify({"error": "Failed to adopt pet"}), 500