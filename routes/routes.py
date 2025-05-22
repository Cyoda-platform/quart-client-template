import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

import httpx
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
class PetFetchRequest:
    status: Optional[str]
    tags: Optional[List[str]]

@dataclass
class OrderCreateRequest:
    petId: int
    quantity: int
    shipDate: str
    complete: bool

pets_cache: Dict[str, List[Dict]] = {}
orders_cache: Dict[str, Dict] = {}

PETSTORE_BASE = "https://petstore.swagger.io/v2"

_job_counter = 0
_job_lock = asyncio.Lock()

async def generate_job_id() -> str:
    global _job_counter
    async with _job_lock:
        _job_counter += 1
        return f"job-{_job_counter}"

def enrich_pet(pet: Dict) -> Dict:
    fun_facts = [
        "Loves chasing laser pointers",
        "Enjoys naps in the sun",
        "Is a picky eater",
        "Has a secret stash of toys",
        "Can do a cute trick"
    ]
    idx = pet.get("id", 0) % len(fun_facts)
    pet["funFact"] = fun_facts[idx]
    return pet

async def fetch_pets_from_petstore(status: Optional[str], tags: Optional[List[str]]) -> List[Dict]:
    async with httpx.AsyncClient() as client:
        url = f"{PETSTORE_BASE}/pet/findByStatus"
        params = {}
        if status:
            params["status"] = status
        try:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception("Failed to fetch pets from Petstore API")
            pets = []
    if tags:
        tags_set = set(tags)
        filtered = []
        for pet in pets:
            pet_tags = set(t["name"] for t in pet.get("tags", []))
            if tags_set.intersection(pet_tags):
                filtered.append(pet)
        pets = filtered
    pets = [enrich_pet(pet) for pet in pets]
    return pets

@app.route("/pets/fetch", methods=["POST"])
@validate_request(PetFetchRequest)
async def pets_fetch(data: PetFetchRequest):
    job_id = await generate_job_id()
    job_entity = {
        "jobId": job_id,
        "status": data.status,
        "tags": data.tags,
        "createdAt": datetime.utcnow().isoformat() + "Z"
    }
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="pet_fetch_job",
            entity_version=ENTITY_VERSION,
            entity=job_entity
        )
    except Exception as e:
        logger.exception(f"Failed to create pet_fetch_job entity: {e}")
        return jsonify({"error": "Failed to start pet fetch job"}), 500
    return jsonify({"message": "Pets fetch started", "jobId": job_id})

@app.route("/pets", methods=["GET"])
async def pets_get():
    if not pets_cache:
        return jsonify([])
    last_job_id = max(pets_cache.keys(), key=lambda k: int(k.split("-")[1]))
    pets = pets_cache.get(last_job_id, [])
    return jsonify(pets)

@app.route("/orders/create", methods=["POST"])
@validate_request(OrderCreateRequest)
async def orders_create(data: OrderCreateRequest):
    order = {
        "petId": data.petId,
        "quantity": data.quantity,
        "shipDate": data.shipDate,
        "complete": data.complete,
        "createdAt": datetime.utcnow().isoformat() + "Z",
    }
    try:
        order_id = await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="order",
            entity_version=ENTITY_VERSION,
            entity=order
        )
    except Exception as e:
        logger.exception(f"Failed to add order: {e}")
        return jsonify({"error": "Failed to create order"}), 500
    orders_cache[str(order_id)] = {**order, "orderId": order_id}
    return jsonify({"orderId": str(order_id), "status": orders_cache[str(order_id)].get("status", "placed")})

@app.route("/orders/<string:order_id>", methods=["GET"])
async def orders_get(order_id: str):
    order = orders_cache.get(order_id)
    if order:
        return jsonify(order)
    try:
        order = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="order",
            entity_version=ENTITY_VERSION,
            technical_id=order_id
        )
        if not order:
            return jsonify({"error": "Order not found"}), 404
        orders_cache[order_id] = order
        return jsonify(order)
    except Exception as e:
        logger.exception(f"Failed to get order with id {order_id}: {e}")
        return jsonify({"error": "Order retrieval failed"}), 500

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
