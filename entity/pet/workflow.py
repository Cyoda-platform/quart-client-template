from datetime import datetime
from typing import Dict

async def process_fetch_pets(entity: Dict) -> None:
    # Business logic for fetching pets would be here
    entity['status'] = 'fetched'
    entity['fetched_at'] = datetime.utcnow().isoformat() + "Z"

async def process_filter_pets(entity: Dict) -> None:
    # Business logic for filtering pets would be here
    entity['status'] = 'filtered'
    entity['filtered_at'] = datetime.utcnow().isoformat() + "Z"

async def process_adopt_pet(entity: Dict) -> None:
    # Business logic for adopting a pet would be here
    entity['status'] = 'pending_adoption'
    entity['adopter_info'] = entity.get('adopter_info', {})

async def process_complete_adoption(entity: Dict) -> None:
    # Mark adoption complete
    entity['status'] = 'adopted'
    entity['adopted_at'] = datetime.utcnow().isoformat() + "Z"

async def process_pet_adoption(entity: Dict) -> None:
    # Workflow orchestration only
    await process_adopt_pet(entity)
    # Simulate some async processing delay or logic if needed
    await process_complete_adoption(entity)