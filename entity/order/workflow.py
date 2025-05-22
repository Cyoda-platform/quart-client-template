import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)
PETSTORE_BASE = "https://petstore.swagger.io/v2"

async def process_validate_pet(order: Dict):
    pet_id = order.get("petId")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{PETSTORE_BASE}/pet/{pet_id}", timeout=10)
            resp.raise_for_status()
            pet = resp.json()
            if pet.get("status") != "available":
                raise ValueError("Pet is not available")
        except Exception as e:
            logger.warning(f"Pet validation failed for petId={pet_id}: {e}")
            order["status"] = "invalid"
            order["validationError"] = "Pet is not available"

async def process_log_order(order: Dict):
    order["processedAt"] = datetime.utcnow().isoformat() + "Z"
    # TODO: Add order log persistence here if needed (outside of entity)
    # Cannot use entity_service to update current entity; just set attributes

async def process_order(order: Dict) -> Dict:
    await process_validate_pet(order)
    if order.get("status") == "invalid":
        return order
    order.setdefault("status", "placed")
    await process_log_order(order)
    return order