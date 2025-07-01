from typing import Dict, Any
import logging
from datetime import datetime
import httpx
from common.config.config import ENTITY_VERSION
from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"

async def process_pet_entity(entity: Dict[str, Any]) -> Dict[str, Any]:
    pet_id = entity.get("id")
    if pet_id is None:
        logger.warning("Pet entity missing 'id', skipping enrichment")
        entity["enrichment_success"] = False
        return entity

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"{PETSTORE_BASE_URL}/pet/{pet_id}")
            r.raise_for_status()
            pet_data = r.json()
        except Exception as e:
            logger.error(f"Failed to fetch pet data for id {pet_id}: {e}")
            logger.exception(e)
            entity["enrichment_success"] = False
            return entity

    if pet_data:
        entity["name"] = pet_data.get("name", entity.get("name"))
        entity["type"] = pet_data.get("category", {}).get("name", entity.get("type"))
        entity["status"] = pet_data.get("status", entity.get("status"))
        entity["photoUrls"] = pet_data.get("photoUrls", entity.get("photoUrls", []))
        entity["last_enriched_at"] = datetime.utcnow().isoformat() + "Z"
        entity["enrichment_success"] = True
    else:
        logger.info(f"No enrichment data for pet id {pet_id}")
        entity["enrichment_success"] = False

    return entity

async def is_enrichment_successful(entity: Dict[str, Any]) -> bool:
    return entity.get("enrichment_success") is True

async def is_enrichment_failed(entity: Dict[str, Any]) -> bool:
    return entity.get("enrichment_success") is False