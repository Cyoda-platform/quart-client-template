from typing import Dict, Any
import logging
from datetime import datetime
from common.config.config import ENTITY_VERSION
from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"

async def process_pet_search_request(entity: Dict[str, Any]) -> Dict[str, Any]:
    pet_type = entity.get("type")
    status = entity.get("status", "available")

    params = {"status": status}
    url = f"{PETSTORE_BASE_URL}/pet/findByStatus"

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(url, params=params)
            r.raise_for_status()
            pets = r.json()
        except Exception as e:
            logger.error(f"Failed to fetch pets in search workflow: {e}")
            logger.exception(e)
            entity["search_success"] = False
            entity["results"] = []
            return entity

    if pet_type:
        pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == pet_type.lower()]

    entity["results"] = [
        {
            "id": p.get("id"),
            "name": p.get("name"),
            "type": p.get("category", {}).get("name", ""),
            "status": p.get("status"),
            "photoUrls": p.get("photoUrls", []),
        }
        for p in pets
    ]
    entity["search_success"] = True
    return entity

async def is_search_successful(entity: Dict[str, Any]) -> bool:
    return entity.get("search_success") is True

async def is_search_failed(entity: Dict[str, Any]) -> bool:
    return entity.get("search_success") is False

async def reset_condition(entity: Dict[str, Any]) -> bool:
    return entity.get("resetRequested") == "true"