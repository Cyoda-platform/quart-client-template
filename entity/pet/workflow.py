from typing import Dict, Any
import logging
import httpx

logger = logging.getLogger(__name__)
PETSTORE_BASE = "https://petstore.swagger.io/v2"

async def process_enrich_pet(entity: Dict[str, Any]) -> None:
    pet_id = entity.get("id")
    if not pet_id:
        logger.warning("Pet entity missing 'id', cannot enrich")
        return

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

async def process_prepare_tags(entity: Dict[str, Any]) -> None:
    if "tags" not in entity or not isinstance(entity.get("tags"), list):
        entity["tags"] = []

async def process_pet(entity: Dict[str, Any]) -> None:
    # Workflow orchestration only
    pet_id = entity.get("id")
    if not pet_id:
        logger.warning("Pet entity missing 'id', cannot enrich")
        return

    missing_info = not (entity.get("name") and entity.get("type") and entity.get("status"))

    await process_prepare_tags(entity)

    if missing_info:
        await process_enrich_pet(entity)