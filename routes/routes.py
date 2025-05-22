import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import Optional, List

import httpx
from quart import Blueprint, jsonify, request
from quart_schema import validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Async-safe in-memory cache for search results only
class AsyncCache:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._store = {}

    async def set(self, key, value):
        async with self._lock:
            self._store[key] = value

    async def get(self, key):
        async with self._lock:
            return self._store.get(key)

search_cache = AsyncCache()

PETSTORE_BASE = "https://petstore.swagger.io/v2"

@dataclass
class PetSearch:
    type: Optional[str]
    status: Optional[str]

@dataclass
class PetAdd:
    name: str
    type: str
    status: str
    tags: Optional[List[str]]

@dataclass
class PetUpdate:
    name: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None

# Workflow function applied to the pet entity asynchronously before persistence.
async def process_pet(entity):
    # Add or update metadata with a unique processing ID
    if "metadata" not in entity or not isinstance(entity["metadata"], dict):
        entity["metadata"] = {}
    entity["metadata"]["processed_at"] = str(uuid.uuid4())

    # Normalize name to title case if present and string
    if "name" in entity and isinstance(entity["name"], str):
        entity["name"] = entity["name"].title()

    # Ensure tags is a list
    if "tags" not in entity or not isinstance(entity["tags"], list):
        entity["tags"] = []

    # Add a default tag if no tags present
    if not entity["tags"]:
        entity["tags"].append("new")

    # Example async side effect (can be replaced with real async calls)
    # await some_async_enrichment(entity)

    # Example of adding supplementary entities of a different model (allowed)
    # but commented out to avoid unintended consequences
    # try:
    #     await entity_service.add_item(
    #         token=cyoda_auth_service,
    #         entity_model="pet_note",
    #         entity_version=ENTITY_VERSION,
    #         entity={"pet_name": entity.get("name", ""), "note": "Added via workflow"}
    #     )
    # except Exception as e:
    #     logger.warning(f"Failed to add supplementary pet_note entity: {e}")

    return entity

@routes_bp.route("/pets/search", methods=["POST"])
@validate_request(PetSearch)
async def pets_search(data: PetSearch):
    pet_type = data.type
    status = data.status

    params = {}
    if status:
        params["status"] = status
    else:
        params["status"] = "available"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{PETSTORE_BASE}/pet/findByStatus", params=params)
            resp.raise_for_status()
            pets_raw = resp.json()

        if pet_type:
            pets_filtered = [p for p in pets_raw if p.get("category", {}).get("name", "").lower() == pet_type.lower()]
        else:
            pets_filtered = pets_raw

        pets = []
        for p in pets_filtered:
            pets.append({
                "id": p.get("id"),
                "name": p.get("name"),
                "type": p.get("category", {}).get("name", "unknown"),
                "status": p.get("status"),
                "tags": [t.get("name") for t in p.get("tags", []) if t.get("name")] if p.get("tags") else []
            })

        search_id = str(uuid.uuid4())
        await search_cache.set(search_id, pets)
        logger.info(f"Stored search results under searchId={search_id}, count={len(pets)}")

        return jsonify({"searchId": search_id})

    except httpx.HTTPError as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pets from Petstore API"}), 502

@routes_bp.route("/pets/search/<search_id>", methods=["GET"])
async def get_search_results(search_id):
    pets = await search_cache.get(search_id)
    if pets is None:
        return jsonify({"error": "searchId not found"}), 404
    return jsonify({"pets": pets})

@routes_bp.route("/pets/add", methods=["POST"])
@validate_request(PetAdd)
async def add_pet(data: PetAdd):
    # Minimal validation already handled by dataclass and validate_request
    pet_data = {
        "name": data.name,
        "type": data.type,
        "status": data.status,
        "tags": data.tags or [],
    }

    try:
        pet_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=pet_data
        )
        logger.info(f"Added new pet with id: {pet_id}")
        message = f"43e Purrfect! Pet '{pet_data['name']}' with ID {pet_id} has been added to your collection! 431"
        return jsonify({"petId": pet_id, "message": message})

    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to add pet"}), 500

@routes_bp.route("/pets/<pet_id>", methods=["GET"])
async def get_pet(pet_id):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=str(pet_id)
        )
        if pet is None:
            return jsonify({"error": "Pet not found"}), 404
        return jsonify(pet)

    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve pet"}), 500

@routes_bp.route("/pets/update/<pet_id>", methods=["POST"])
@validate_request(PetUpdate)
async def update_pet(data: PetUpdate, pet_id):
    update_data = {}
    if data.name is not None:
        update_data["name"] = data.name.title() if isinstance(data.name, str) else data.name
    if data.status is not None:
        update_data["status"] = data.status
    if data.tags is not None:
        update_data["tags"] = data.tags

    if not update_data:
        return jsonify({"error": "No valid fields to update"}), 400

    try:
        await entity_service.update_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            entity=update_data,
            technical_id=str(pet_id),
            meta={}
        )
        message = f"43e Pet ID {pet_id} updated with love and care! 496"
        logger.info(f"Updated pet {pet_id} with {update_data}")
        return jsonify({"message": message})

    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to update pet"}), 500