from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def process_validate_pet_exists(entity: dict):
    pet_id = entity.get("petId")
    if not pet_id:
        logger.warning("favorite_pet entity missing petId")
        entity['valid'] = False
        return

    # TODO: Replace this mock check with real pet existence check
    # For prototype, we simulate pet exists if petId is an integer > 0
    if isinstance(pet_id, int) and pet_id > 0:
        entity['valid'] = True
    else:
        logger.warning(f"Trying to favorite pet that does not exist: {pet_id}")
        entity['valid'] = False

async def process_set_favorited_at(entity: dict):
    if entity.get('valid'):
        entity['favorited_at'] = datetime.utcnow().isoformat() + 'Z'

async def process_favorite_pet(entity: dict) -> dict:
    # Workflow orchestration only
    await process_validate_pet_exists(entity)
    await process_set_favorited_at(entity)
    return entity