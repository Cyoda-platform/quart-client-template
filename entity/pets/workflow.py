import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_fetch(entity: Dict[str, Any]) -> None:
    # Simulate fetching pets from external API and storing in entity['pets']
    # TODO: Replace mock with actual fetch logic if needed
    entity['pets'] = entity.get('pets', [])
    entity['status'] = 'fetched'
    logger.info(f"Fetched {len(entity['pets'])} pets")

async def process_enrich(entity: Dict[str, Any]) -> None:
    # Enrich each pet with description and other business logic
    pets = entity.get('pets', [])
    for pet in pets:
        pet.setdefault("description", f"A lovely {pet.get('category', {}).get('name', 'pet')}.")
    entity['status'] = 'enriched'
    logger.info("Enriched pets with descriptions")

async def process_recommend(entity: Dict[str, Any]) -> None:
    # Provide recommendations based on available pets and preferences in entity
    preferred_type = entity.get('preferredType')
    max_results = entity.get('maxResults', 3)
    pets = entity.get('pets', [])
    candidates = [p for p in pets if not preferred_type or p.get('category', {}).get('name', '').lower() == preferred_type.lower()]
    if preferred_type and not candidates:
        candidates = pets
    entity['recommendations'] = candidates[:max_results]
    entity['status'] = 'recommended'
    logger.info(f"Generated {len(entity['recommendations'])} recommendations")

async def process_pets(entity: Dict[str, Any]) -> None:
    # Workflow orchestration only - no business logic here
    if entity.get('action') == 'fetch':
        await process_fetch(entity)
        await process_enrich(entity)
    elif entity.get('action') == 'recommend':
        await process_recommend(entity)
    else:
        # Default processing or no-op
        pass