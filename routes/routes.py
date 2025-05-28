from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from quart import Blueprint, request, jsonify, abort
from quart_schema import validate_request
import httpx
from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

PETSTORE_BASE = "https://petstore.swagger.io/v2"

@dataclass
class PetSearch:
    type: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None

@dataclass
class OrderRequest:
    petId: int
    quantity: int

orders_cache: Dict[int, Dict[str, Any]] = {}
order_id_seq = 1
lock = asyncio.Lock()

# Workflow for 'pet' entity - enrich pet with external API data if missing critical info
async def process_pet(entity: Dict[str, Any]) -> None:
    pet_id = entity.get("id")
    if not pet_id:
        logger.warning("Pet entity missing 'id', cannot enrich")
        return

    missing_info = False
    if not entity.get("name") or not entity.get("type") or not entity.get("status"):
        missing_info = True

    if "tags" not in entity or not isinstance(entity.get("tags"), list):
        entity["tags"] = []

    if missing_info:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{PETSTORE_BASE}/pet/{pet_id}")
                resp.raise_for_status()
                pet_data = resp.json()
                entity["name"] = entity.get("name") or pet_data.get("name", "")
                entity["type"] = entity.get("type") or pet_data.get("category", {}).get("name", "")
                entity["status"] = entity.get("status") or pet_data.get("status", "")
                entity["tags"] = [tag.get("name", "") for tag in pet_data.get("tags", [])]
        except Exception as e:
            logger.warning(f"Failed to enrich pet entity {pet_id} from external API: {e}")

# Workflow for 'order' entity - add timestamp, verify pet existence and enrich order with pet info
async def process_order(entity: Dict[str, Any]) -> None:
    if "createdAt" not in entity:
        entity["createdAt"] = datetime.utcnow().isoformat() + "Z"

    pet_id = entity.get("petId")
    if not pet_id:
        logger.warning("Order missing petId")
        return

    pet_str_id = str(pet_id)
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_str_id
        )
    except Exception:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{PETSTORE_BASE}/pet/{pet_id}")
                resp.raise_for_status()
                pet_data = resp.json()
                pet_entity = {
                    "id": pet_data["id"],
                    "name": pet_data.get("name", ""),
                    "type": pet_data.get("category", {}).get("name", ""),
                    "status": pet_data.get("status", ""),
                    "tags": [tag.get("name", "") for tag in pet_data.get("tags", [])]
                }
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="pet",
                    entity_version=ENTITY_VERSION,
                    entity=pet_entity
                )
                pet = pet_entity
        except Exception as e:
            logger.warning(f"Failed to fetch pet {pet_id} for order enrichment: {e}")
            pet = None

    if pet:
        entity["petName"] = pet.get("name", "")
        entity["petType"] = pet.get("type", "")
        entity["petStatus"] = pet.get("status", "")

# Workflow for 'pet_search' entity - perform search, filter results, update pet entities, add pets list
async def process_pet_search(entity: Dict[str, Any]) -> None:
    pet_type = entity.get("type")
    status = entity.get("status") or "available"
    tags_filter = set(t.lower() for t in entity.get("tags", []))

    pets = []
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{PETSTORE_BASE}/pet/findByStatus", params={"status": status})
            resp.raise_for_status()
            pets = resp.json()
    except Exception as e:
        logger.warning(f"Pet search external API call failed: {e}")
        entity["pets"] = []
        return

    def pet_matches(pet):
        if pet_type and pet.get("category", {}).get("name", "").lower() != pet_type.lower():
            return False
        if tags_filter:
            pet_tags = {tag.get("name", "").lower() for tag in pet.get("tags", [])}
            if not tags_filter.issubset(pet_tags):
                return False
        return True

    filtered_pets = [
        {
            "id": pet["id"],
            "name": pet.get("name", ""),
            "type": pet.get("category", {}).get("name", ""),
            "status": pet.get("status", ""),
            "tags": [tag.get("name", "") for tag in pet.get("tags", [])]
        }
        for pet in pets if pet_matches(pet)
    ]

    for pet in filtered_pets:
        try:
            pet_str_id = str(pet["id"])
            await entity_service.update_item(
                token=cyoda_auth_service,
                entity_model="pet",
                entity_version=ENTITY_VERSION,
                entity=pet,
                technical_id=pet_str_id,
                meta={}
            )
        except Exception as e:
            logger.warning(f"Failed to update pet entity {pet['id']}: {e}")

    entity["pets"] = filtered_pets

@routes_bp.route("/pets/search", methods=["POST"])
@validate_request(PetSearch)
async def search_pets(data: PetSearch):
    data_dict = data.__dict__
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet_search",
            entity_version=ENTITY_VERSION,
            entity=data_dict
        )
    except Exception as e:
        logger.error(f"Failed to initiate pet_search entity: {e}")
        return jsonify({"pets": []}), 503
    pets = data_dict.get("pets", [])
    return jsonify({"pets": pets})

@routes_bp.route("/pets/order", methods=["POST"])
@validate_request(OrderRequest)
async def place_order(data: OrderRequest):
    pet_id = data.petId
    quantity = data.quantity

    if quantity <= 0:
        abort(400, "Invalid quantity")

    async with lock:
        global order_id_seq
        current_order_id = order_id_seq
        order_id_seq += 1

    order_entity = {
        "orderId": current_order_id,
        "petId": pet_id,
        "quantity": quantity,
        "status": "placed",
        "placedAt": datetime.utcnow().isoformat() + "Z"
    }
    orders_cache[current_order_id] = order_entity

    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="order",
            entity_version=ENTITY_VERSION,
            entity=order_entity
        )
    except Exception as e:
        logger.error(f"Failed to add order entity: {e}")

    return jsonify({
        "orderId": order_entity["orderId"],
        "petId": order_entity["petId"],
        "quantity": order_entity["quantity"],
        "status": order_entity["status"]
    })

@routes_bp.route("/pets/<string:pet_id>", methods=["GET"])
async def get_pet(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
    except Exception as e:
        logger.warning(f"Pet {pet_id} not found: {e}")
        abort(404, "Pet not found")
    return jsonify(pet)

@routes_bp.route("/orders/<int:order_id>", methods=["GET"])
async def get_order(order_id: int):
    order = orders_cache.get(order_id)
    if not order:
        abort(404, "Order not found")
    return jsonify({
        "orderId": order["orderId"],
        "petId": order["petId"],
        "quantity": order["quantity"],
        "status": order["status"]
    })