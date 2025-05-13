from dataclasses import dataclass
import logging
from datetime import datetime
from typing import Dict, Any
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request
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

PETSTORE_BASE = "https://petstore.swagger.io/v2"

@dataclass
class PetSearchFilters:
    status: str = None
    category: str = None
    name: str = None

@dataclass
class OrderRequest:
    petId: int
    quantity: int
    shipDate: str
    status: str
    complete: bool

async def fetch_pets_from_petstore(filters: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{PETSTORE_BASE}/pet/findByStatus"
    params = {"status": filters.get("status") or "available,pending,sold"}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception("Failed fetching pets from Petstore API")
            pets = []
    cat_f = (filters.get("category") or "").lower()
    name_f = (filters.get("name") or "").lower()
    def matches(pet):
        if cat_f:
            if (pet.get("category") or {}).get("name", "").lower() != cat_f:
                return False
        if name_f:
            if name_f not in (pet.get("name") or "").lower():
                return False
        return True
    filtered = [pet for pet in pets if matches(pet)]
    result = []
    for pet in filtered:
        pet_obj = {
            "id": pet.get("id"),
            "name": pet.get("name"),
            "category": pet.get("category", {}).get("name") if pet.get("category") else None,
            "status": pet.get("status"),
            "photoUrls": pet.get("photoUrls", []),
            "tags": [t.get("name") for t in pet.get("tags", [])] if pet.get("tags") else []
        }
        result.append(pet_obj)
    return {"pets": result}

@app.route("/pets/search", methods=["POST"])
@validate_request(PetSearchFilters)
async def pets_search(filters: PetSearchFilters):
    result = await fetch_pets_from_petstore(filters.__dict__)
    return jsonify(result)

@app.route("/pets/<string:pet_id>", methods=["GET"])
async def pet_details(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Pet not found"}), 404
    if not pet:
        return jsonify({"error": "Pet not found"}), 404
    return jsonify(pet)

async def place_order_petstore(order: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{PETSTORE_BASE}/store/order"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=order, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            logger.exception("Error placing order to Petstore")
            return {"error": "Petstore order placement failed"}

async def process_order(entity: Dict[str, Any]):
    entity.setdefault('createdAt', datetime.utcnow().isoformat())
    entity['orderStatus'] = 'processing'
    petstore_response = await place_order_petstore(entity)
    if "error" in petstore_response:
        entity['orderStatus'] = 'failed'
        entity['failureReason'] = petstore_response['error']
        logger.error(f"Failed to place order id={entity.get('id')}: {petstore_response['error']}")
    else:
        entity['orderStatus'] = 'completed'
        entity['petstoreOrderId'] = petstore_response.get('id')
        entity['completedAt'] = datetime.utcnow().isoformat()
    # Example of adding supplementary entity, commented out to avoid issues
    # try:
    #     pet_details = await entity_service.get_item(
    #         token=cyoda_auth_service,
    #         entity_model="pet",
    #         entity_version=ENTITY_VERSION,
    #         technical_id=str(entity.get("petId"))
    #     )
    #     if pet_details:
    #         await entity_service.add_item(
    #             token=cyoda_auth_service,
    #             entity_model="order_pet_details",
    #             entity_version=ENTITY_VERSION,
    #             entity={"orderId": entity.get("id"), "pet": pet_details}
    #         )
    # except Exception:
    #     logger.exception("Failed to fetch or add supplementary pet details")

@app.route("/orders", methods=["POST"])
@validate_request(OrderRequest)
async def orders_place(data: OrderRequest):
    order_payload = {
        "petId": data.petId,
        "quantity": data.quantity,
        "shipDate": data.shipDate,
        "status": data.status,
        "complete": data.complete,
    }
    try:
        order_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="order",
            entity_version=ENTITY_VERSION,
            entity=order_payload
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to place order"}), 500
    return jsonify({"orderId": str(order_id), "status": "placed", "message": "Order successfully placed"})

@app.route("/orders/<string:order_id>", methods=["GET"])
async def orders_get(order_id: str):
    try:
        order = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="order",
            entity_version=ENTITY_VERSION,
            technical_id=order_id
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Order not found"}), 404
    if not order:
        return jsonify({"error": "Order not found"}), 404
    return jsonify(order)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)