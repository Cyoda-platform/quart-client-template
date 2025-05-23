from datetime import datetime
import httpx
import logging

logger = logging.getLogger(__name__)
PETSTORE_BASE_URL = "https://petstore3.swagger.io/api/v3"

async def process_normalize_status(entity: dict):
    if 'status' in entity and isinstance(entity['status'], str):
        entity['status'] = entity['status'].lower()

async def process_add_timestamp(entity: dict):
    entity['processed_at'] = datetime.utcnow().isoformat() + 'Z'

async def process_enrich_petstore_data(entity: dict):
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            params = {}
            if entity.get('status'):
                params['status'] = entity['status']
            response = await client.get(f"{PETSTORE_BASE_URL}/pet/findByStatus", params=params)
            response.raise_for_status()
            pets = response.json()

            filtered = []
            name_lower = entity.get('name', '').lower()
            type_lower = entity.get('type', '').lower()
            for pet in pets:
                pet_type = pet.get('category', {}).get('name', '').lower()
                pet_name = pet.get('name', '').lower()
                if pet_type == type_lower and name_lower in pet_name:
                    filtered.append(pet)

            entity['petstore_matches_count'] = len(filtered)
            entity['petstore_sample_matches'] = filtered[:3]

    except Exception as e:
        logger.warning(f"Failed to enrich pet entity with petstore data: {e}")

async def process_pet(entity: dict):
    # Workflow orchestration only
    await process_normalize_status(entity)
    await process_add_timestamp(entity)
    await process_enrich_petstore_data(entity)
```