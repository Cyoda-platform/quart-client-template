import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def process_pet_matchmake_job(entity: dict) -> None:
    entity["status"] = "processing"
    entity["startedAt"] = datetime.utcnow().isoformat()
    try:
        await process_fetch_pets(entity)
        await process_calculate_matches(entity)
        entity["status"] = "completed"
        entity["completedAt"] = datetime.utcnow().isoformat()
    except Exception as e:
        logger.exception("Failed processing pet_matchmake_job")
        entity["status"] = "failed"
        entity["error"] = str(e)

async def process_fetch_pets(entity: dict) -> None:
    preferred_type = entity.get("preferredType")
    preferred_status = entity.get("preferredStatus")
    pets = await fetch_pets_from_petstore(preferred_type, preferred_status)
    entity["fetchedPets"] = pets  # temporarily store fetched pets for next step

async def process_calculate_matches(entity: dict) -> None:
    preferred_type = entity.get("preferredType")
    preferred_status = entity.get("preferredStatus")
    pets = entity.get("fetchedPets", [])
    matched_pets = []
    for pet in pets:
        score = await calculate_match_score(pet, preferred_type, preferred_status)
        if score > 0:
            p = pet.copy()
            p["matchScore"] = round(score, 2)
            matched_pets.append(p)
        try:
            # TODO: Add pet entities with a separate workflow outside this entity's state
            pass
        except Exception:
            logger.exception("Failed to add pet entity in pet_matchmake_job workflow")
    entity["result"] = {"matchedPets": matched_pets}
    entity.pop("fetchedPets", None)  # cleanup temporary data