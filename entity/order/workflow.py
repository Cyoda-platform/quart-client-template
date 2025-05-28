from typing import Dict, Any
import logging
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)
PETSTORE_BASE = "https://petstore.swagger.io/v2"
ENTITY_VERSION = ENTITY_VERSION  # imported constant
entity_service = entity_service  # service instance
cyoda_auth_service = cyoda_auth_service  # service instance

async def process_fetch_pet(entity: Dict[str, Any]) -> None:
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
        entity["petData"] = pet
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
                # Add pet entity asynchronously, but do not update current entity here
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="pet",
                    entity_version=ENTITY_VERSION,
                    entity=pet_entity,
                    workflow=process_fetch_pet
                )
                entity["petData"] = pet_entity
        except Exception as e:
            logger.warning(f"Failed to fetch pet {pet_id} for order enrichment: {e}")
            entity["petData"] = None

async def process_enrich_order(entity: Dict[str, Any]) -> None:
    pet = entity.get("petData")
    if pet:
        entity["petName"] = pet.get("name", "")
        entity["petType"] = pet.get("type", "")
        entity["petStatus"] = pet.get("status", "")

async def process_order(entity: Dict[str, Any]) -> None:
    # Workflow orchestration only - no business logic here
    if "createdAt" not in entity:
        entity["createdAt"] = datetime.utcnow().isoformat() + "Z"

    await process_fetch_pet(entity)
    await process_enrich_order(entity)