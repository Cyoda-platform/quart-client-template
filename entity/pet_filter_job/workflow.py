from datetime import datetime
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_fetch_pets(entity: dict):
    # Business logic: fetch pets from external source (mocked here)
    # TODO: Replace with real external API call
    import random
    pets = []
    for i in range(10):
        pets.append({
            "id": i + 1,
            "name": f"Pet{i+1}",
            "type": "cat" if i % 2 == 0 else "dog",
            "age": random.randint(1, 10),
            "status": "available",
            "fun_category": None,
        })
    entity["pets"] = pets

async def process_apply_filter(entity: dict):
    # Business logic: apply filtering and fun_category assignment
    pets = entity.get("pets", [])
    min_age = entity.get("min_age")
    max_age = entity.get("max_age")
    fun_category = entity.get("fun_category")

    filtered = []
    for pet in pets:
        age = pet.get("age")
        if min_age is not None and (age is None or age < min_age):
            continue
        if max_age is not None and (age is None or age > max_age):
            continue
        pet_copy = pet.copy()
        if fun_category:
            pet_copy["fun_category"] = fun_category
        else:
            if age is not None:
                if age <= 3:
                    pet_copy["fun_category"] = "playful"
                elif age >= 7:
                    pet_copy["fun_category"] = "sleepy"
                else:
                    pet_copy["fun_category"] = "neutral"
            else:
                pet_copy["fun_category"] = "unknown"
        filtered.append(pet_copy)
    entity["filtered_pets"] = filtered

async def process_pet_filter_job(entity: dict):
    if entity.get("status") in ("completed", "failed"):
        return

    entity["status"] = "processing"
    entity["startedAt"] = datetime.utcnow().isoformat()

    try:
        # Workflow orchestration only - call business logic funcs
        await process_fetch_pets(entity)
        await process_apply_filter(entity)

        entity["status"] = "completed"
        entity["completedAt"] = datetime.utcnow().isoformat()
        entity["result_count"] = len(entity.get("filtered_pets", []))

    except Exception as e:
        logger.exception("Error in pet_filter_job workflow")
        entity["status"] = "failed"
        entity["error"] = str(e)
        entity["completedAt"] = datetime.utcnow().isoformat()
