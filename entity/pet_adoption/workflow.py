from datetime import datetime
import httpx
import logging
from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

class Cache:
    def __init__(self):
        import asyncio
        self.adopted_pets = {}
        self.lock = asyncio.Lock()

cache = Cache()

async def condition_pet_id_present(entity: dict) -> bool:
    return "id" in entity and isinstance(entity["id"], int)

async def condition_pet_id_absent(entity: dict) -> bool:
    return not ("id" in entity and isinstance(entity["id"], int))

async def condition_pet_exists(entity: dict) -> bool:
    pet_id = entity.get("id")
    if not pet_id:
        return False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"https://petstore3.swagger.io/api/v3/pet/{pet_id}")
            r.raise_for_status()
            pet = r.json()
            entity["_pet_data"] = pet
            return True
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return False
        logger.exception(e)
        return False
    except Exception as e:
        logger.exception(e)
        return False

async def condition_pet_not_exists(entity: dict) -> bool:
    return not await condition_pet_exists(entity)

async def condition_pet_available(entity: dict) -> bool:
    pet = entity.get("_pet_data", {})
    return pet.get("status") == "available"

async def condition_pet_not_available(entity: dict) -> bool:
    pet = entity.get("_pet_data", {})
    return pet.get("status") != "available"

async def condition_pet_already_adopted(entity: dict) -> bool:
    pet_id = entity.get("id")
    if not pet_id:
        return False
    async with cache.lock:
        return pet_id in cache.adopted_pets

async def enrich_entity_with_pet_data(entity: dict):
    pet = entity.get("_pet_data", {})
    entity["name"] = pet.get("name")
    entity["type"] = pet.get("category", {}).get("name")
    entity["adoptionDate"] = datetime.utcnow().isoformat() + "Z"
    entity["message"] = f"Congratulations on adopting {entity['name']}! 🎉🐾"

async def persist_adoption(entity: dict):
    pet_id = entity.get("id")
    if not pet_id:
        logger.error("persist_adoption called without pet id")
        return
    async with cache.lock:
        cache.adopted_pets[pet_id] = {
            "id": pet_id,
            "name": entity.get("name"),
            "type": entity.get("type"),
            "adoptionDate": entity.get("adoptionDate"),
            "message": entity.get("message"),
        }