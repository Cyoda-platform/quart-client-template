import asyncio
from datetime import datetime
import httpx

async def not_needs_processing(entity: dict) -> bool:
    return entity.get("processed_at") is not None

async def needs_processing(entity: dict) -> bool:
    return entity.get("processed_at") is None

async def process_petsearch(entity: dict):
    pet_type = entity.get("type")
    status = entity.get("status") or "available"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            params = {"status": status}
            resp = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params=params)
            resp.raise_for_status()
            pets_raw = resp.json()

        if pet_type:
            pets_filtered = [p for p in pets_raw if p.get("category") and p["category"].get("name", "").lower() == pet_type.lower()]
        else:
            pets_filtered = pets_raw

        sem = asyncio.Semaphore(10)

        async def save_pet(pet):
            pet_data = {
                "id": str(pet.get("id")),
                "name": pet.get("name"),
                "type": pet.get("category", {}).get("name", None),
                "status": pet.get("status"),
                "photoUrls": pet.get("photoUrls", []),
            }
            try:
                await entity_service.add_item(
                    token=cyoda_auth_service,
                    entity_model="pet",
                    entity_version=ENTITY_VERSION,
                    entity=pet_data,
                    workflow=process_pet,
                )
            except Exception as e:
                logger.exception(f"Failed to save pet {pet_data.get('id')}: {e}")

        async def sem_save_pet(p):
            async with sem:
                await save_pet(p)

        await asyncio.gather(*(sem_save_pet(p) for p in pets_filtered))

    except Exception as e:
        logger.exception(f"Failed to process petsearch entity: {e}")

    entity["processed_at"] = datetime.utcnow().isoformat()
    return entity