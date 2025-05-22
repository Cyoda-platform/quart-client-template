from datetime import datetime

async def process_fetch(entity: dict):
    # Business logic: fetch and process external pets data
    # TODO: implement external API fetch and update entity with results
    entity['status'] = 'fetched'
    entity['processedAt'] = datetime.utcnow().isoformat()

async def process_cache(entity: dict):
    # Business logic: cache processed pets data
    # TODO: implement caching logic here
    entity['status'] = 'cached'
    entity['processedAt'] = datetime.utcnow().isoformat()

async def process_adoption_request(entity: dict):
    # Business logic: process adoption request
    # TODO: implement adoption request handling
    entity['status'] = 'adoption_requested'
    entity['processedAt'] = datetime.utcnow().isoformat()

async def process_pet(entity: dict) -> dict:
    # Workflow orchestration only
    state = entity.get('state')
    if state == 'fetching':
        await process_fetch(entity)
    elif state == 'caching':
        await process_cache(entity)
    elif state == 'adoption':
        await process_adoption_request(entity)
    else:
        entity['status'] = 'unknown_state'
        entity['processedAt'] = datetime.utcnow().isoformat()
    return entity