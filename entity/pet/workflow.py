from datetime import datetime
import uuid
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

async def get_random_pet_fact() -> str:
    # Placeholder for actual async call to fetch a random pet fact
    ...

async def fetch_pet_from_petstore(pet_id: str) -> Optional[Dict[str, Any]]:
    # Placeholder for actual async call to fetch pet data from petstore API
    ...

async def process_add(entity: Dict[str, Any]):
    if not entity.get("id"):
        entity["id"] = str(uuid.uuid4())
    try:
        fact = await get_random_pet_fact()
        entity["funFact"] = fact
    except Exception as e:
        logger.warning(f"Failed to fetch random pet fact: {e}")
    petstore_data = await fetch_pet_from_petstore(entity["id"])
    if petstore_data:
        for k, v in petstore_data.items():
            if k not in entity:
                entity[k] = v

async def process_update(entity: Dict[str, Any]):
    pet_id = entity.get("id")
    if pet_id:
        petstore_data = await fetch_pet_from_petstore(pet_id)
        if petstore_data:
            for k, v in petstore_data.items():
                if k not in entity:
                    entity[k] = v

async def process_pet(entity: Dict[str, Any]) -> Dict[str, Any]:
    """
    Workflow function applied to pet entity before persistence.
    Handles async tasks such as enrichment, validation, supplement data fetching.
    """
    action = entity.get("action")

    # Remove 'action' before persistence - model should not store it
    if "action" in entity:
        del entity["action"]

    # Add processedAt timestamp always
    entity["processedAt"] = datetime.utcnow().isoformat()

    if action == "add":
        await process_add(entity)
    elif action == "update":
        await process_update(entity)
    # For other actions or no action: just add processedAt timestamp

    return entity