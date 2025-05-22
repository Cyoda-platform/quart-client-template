import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

pets_cache: Dict[str, List[Dict]] = {}
orders_cache: Dict[int, Dict] = {}

PETSTORE_BASE = "https://petstore.swagger.io/v2"

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

async def validate_pet_availability(pet_id: int) -> bool:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PETSTORE_BASE}/pet/{pet_id}", timeout=10)
            resp.raise_for_status()
            pet = resp.json()
            return pet.get("status") == "available"
        except Exception as e:
            logger.exception(f"Failed to validate pet availability for petId={pet_id}")
            return False

async def process_pet_fetch_job(entity: Dict) -> Dict:
    # Workflow orchestration only
    job_id = entity.get("jobId")
    status = entity.get("status")
    tags = entity.get("tags")
    await process_fetch_pets(entity)
    entity["status"] = "completed"
    entity["petsCount"] = len(pets_cache.get(job_id, []))
    return entity

async def process_fetch_pets(entity: Dict):
    job_id = entity.get("jobId")
    status = entity.get("status")
    tags = entity.get("tags")
    logger.info(f"Starting pet fetch job {job_id} with status={status}, tags={tags}")
    pets = await fetch_pets_from_petstore(status, tags)
    pets_cache[job_id] = pets
    logger.info(f"Completed pet fetch job {job_id}, fetched {len(pets)} pets")

async def process_order_create_job(entity: Dict) -> Dict:
    pet_id = entity.get("petId")
    available = await process_validate_pet_availability(entity)
    if not available:
        entity["error"] = "Pet is not available"
        entity["status"] = "failed"
        return entity
    await process_store_order(entity)
    entity["status"] = "placed"
    return entity

async def process_validate_pet_availability(entity: Dict) -> bool:
    pet_id = entity.get("petId")
    return await validate_pet_availability(pet_id)

async def process_store_order(entity: Dict):
    pet_id = entity.get("petId")
    quantity = entity.get("quantity", 1)
    ship_date = entity.get("shipDate")
    complete = entity.get("complete", False)
    # Generate orderId here as a simple increment
    order_id = max(orders_cache.keys(), default=0) + 1
    order = {
        "orderId": order_id,
        "petId": pet_id,
        "quantity": quantity,
        "shipDate": ship_date,
        "complete": complete,
        "status": "placed",
        "createdAt": datetime.utcnow().isoformat() + "Z",
    }
    orders_cache[order_id] = order
    entity["orderId"] = order_id