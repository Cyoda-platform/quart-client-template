from typing import Dict

async def process_subscriber(entity: Dict) -> Dict:
    # Workflow orchestration for subscriber entity
    if entity.get('state') == 'new':
        await process_normalize_email(entity)
        entity['state'] = 'processed'
    return entity

async def process_normalize_email(entity: Dict):
    if 'email' in entity:
        entity['email'] = entity['email'].lower()