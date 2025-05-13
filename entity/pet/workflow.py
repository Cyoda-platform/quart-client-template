from datetime import datetime

async def process_pet(entity: dict) -> dict:
    # workflow orchestration only - delegate to processing functions
    await process_normalize_fields(entity)
    await process_handle_photos(entity)
    entity['processed_at'] = datetime.utcnow().isoformat() + "Z"
    return entity

async def process_normalize_fields(entity: dict):
    if 'type' in entity and isinstance(entity['type'], str):
        entity['type'] = entity['type'].lower()
    if 'status' in entity and isinstance(entity['status'], str):
        entity['status'] = entity['status'].lower()

async def process_handle_photos(entity: dict):
    if 'photoUrls' in entity:
        if isinstance(entity['photoUrls'], str):
            entity['photoUrls'] = [url.strip() for url in entity['photoUrls'].split(",") if url.strip()]
        elif not isinstance(entity['photoUrls'], list):
            entity['photoUrls'] = []