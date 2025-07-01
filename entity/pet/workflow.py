from datetime import datetime

async def fetch_pets(entity: dict):
    # Simulate fetching pets data and adding it to entity
    entity["pets"] = [{"id": 1, "name": "Whiskers"}, {"id": 2, "name": "Paws"}]
    entity["workflowProcessed"] = True

async def process_pet(entity: dict):
    """
    Workflow function applied to the 'pet' entity asynchronously before persistence.
    Modify the entity as needed. For example, add a timestamp or default values.
    Cannot add/update/delete 'pet' entity inside this function to avoid recursion.
    """
    entity["processed_at"] = datetime.utcnow().isoformat()
    return entity

async def condition_is_new(entity: dict) -> bool:
    # Condition to check if entity is new
    return entity.get("state") == "new"

async def condition_is_processed(entity: dict) -> bool:
    # Condition to check if entity is processed
    return entity.get("state") == "processed"

async def condition_has_data(entity: dict) -> bool:
    # Condition to check if entity has data to proceed
    pets = entity.get("pets")
    return bool(pets and len(pets) > 0)

async def cache_pets(entity: dict):
    # Simulate caching pets data
    pets = entity.get("pets")
    if pets:
        entity["cached_pets"] = pets
    entity["workflowProcessed"] = True

async def publish_pets(entity: dict):
    # Simulate publishing pets data
    cached_pets = entity.get("cached_pets")
    if cached_pets:
        entity["published"] = True
    entity["workflowProcessed"] = True