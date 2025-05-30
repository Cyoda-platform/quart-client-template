from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def process_validate_rating(entity: dict):
    rating = entity.get("rating")
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        raise ValueError("rating must be an integer between 1 and 5")

async def process_set_timestamps(entity: dict):
    now_iso = datetime.utcnow().isoformat() + "Z"
    entity.setdefault("processedAt", now_iso)
    if "submittedAt" not in entity:
        entity["submittedAt"] = now_iso

async def process_create_review_summary(entity: dict):
    now_iso = entity.get("processedAt") or datetime.utcnow().isoformat() + "Z"
    entity["review_summary"] = {
        "userId": entity.get("userId"),
        "petId": entity.get("petId"),
        "rating": entity.get("rating"),
        "timestamp": now_iso
    }

async def process_pet_review(entity: dict) -> dict:
    # Workflow orchestration only - no business logic here
    await process_validate_rating(entity)
    await process_set_timestamps(entity)
    await process_create_review_summary(entity)
    return entity