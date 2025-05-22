import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def fetch_pets_from_petstore(type_: Optional[str], status: Optional[str]) -> List[Dict[str, Any]]:
    import httpx
    url = "https://petstore.swagger.io/v2/pet/findByStatus"
    status_query = status if status else "available"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params={"status": status_query})
            r.raise_for_status()
            pets = r.json()
    except Exception as e:
        logger.exception("Failed to fetch pets from Petstore API")
        raise
    if type_:
        pets = [p for p in pets if p.get("category", {}).get("name", "").lower() == type_.lower()]
    return pets

async def process_pet_entity(entity: Dict[str, Any]) -> None:
    entity.setdefault("description", f"A lovely {entity.get('category', {}).get('name', 'pet')}.")
    logger.debug(f"Processed pet entity before persistence: {entity.get('id')}")

async def process_pets_fetch_job(entity: Dict[str, Any]) -> None:
    # Workflow orchestration only, no business logic here
    job_id = entity.get("job_id")
    if not job_id:
        job_id = datetime.utcnow().isoformat(timespec='milliseconds').replace(":", "-")
        entity["job_id"] = job_id
    entity["status"] = "processing"
    entity["startedAt"] = datetime.utcnow().isoformat()

    type_ = entity.get("type")
    status_filter = entity.get("status_filter") or entity.get("status")

    try:
        pets = await fetch_pets_from_petstore(type_, status_filter)
        # Process each pet entity
        for pet in pets:
            pet_id = pet.get("id")
            if pet_id is None:
                continue
            await process_pet_entity(pet)
            # TODO: Persist pet entity to storage - outside this function
            # This function modifies the pet dict in place but does not persist
        entity["status"] = "completed"
        entity["count"] = len(pets)
        entity["completedAt"] = datetime.utcnow().isoformat()
        logger.info(f"Fetch job {job_id} completed, {len(pets)} pets processed.")
    except Exception as e:
        entity["status"] = "failed"
        entity["error"] = str(e)
        entity["completedAt"] = datetime.utcnow().isoformat()
        logger.exception(f"Fetch job {job_id} failed: {e}")