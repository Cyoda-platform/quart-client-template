from datetime import datetime
from typing import Dict, Any

async def process_normalize_name(entity: Dict[str, Any]) -> None:
    if 'name' in entity and isinstance(entity['name'], str):
        entity['name'] = entity['name'].title()

async def process_enrich_category(entity: Dict[str, Any]) -> None:
    category = entity.get('category')
    if category and isinstance(category, dict) and 'id' in category:
        category['description'] = f"Category {category['id']} description (enriched)"

async def process_transform_tags(entity: Dict[str, Any]) -> None:
    if 'tags' in entity and isinstance(entity['tags'], list):
        entity['tags'] = [tag.upper() if isinstance(tag, str) else tag for tag in entity['tags']]

async def process_add_processed_timestamp(entity: Dict[str, Any]) -> None:
    entity['processed_at'] = datetime.utcnow().isoformat()

async def process_pet(entity: Dict[str, Any]) -> None:
    # Orchestrate workflow steps without business logic here
    await process_add_processed_timestamp(entity)
    await process_normalize_name(entity)
    await process_enrich_category(entity)
    await process_transform_tags(entity)