from datetime import datetime
from typing import Dict

async def process_validate_adoptionrequest(entity: Dict):
    pet_id = entity.get("petId")
    adopter = entity.get("adopter", {})
    name = adopter.get("name")
    contact = adopter.get("contact")

    if not pet_id or not name or not contact:
        raise ValueError("Missing petId or adopter information")

async def process_check_pet_exists(entity: Dict):
    pet_id = entity.get("petId")
    pet = await entity_service.get_item(
        token=cyoda_auth_service,
        entity_model=PET_ENTITY_NAME,
        entity_version=ENTITY_VERSION,
        technical_id=pet_id,
    )
    if not pet:
        raise ValueError(f"Pet with id {pet_id} not found")

async def process_update_status_and_timestamp(entity: Dict):
    entity["requestedAt"] = datetime.utcnow().isoformat()
    entity["status"] = "pending"

async def process_adoptionrequest(entity: Dict) -> Dict:
    # Workflow orchestration only
    await process_validate_adoptionrequest(entity)
    await process_check_pet_exists(entity)
    await process_update_status_and_timestamp(entity)
    # Additional workflow steps can be added here
    return entity