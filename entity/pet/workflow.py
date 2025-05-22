from datetime import datetime
from typing import Dict

async def process_pet(entity: Dict) -> None:
    # Workflow orchestration: call business logic functions in order
    await process_normalize_status(entity)
    await process_add_last_processed(entity)

async def process_normalize_status(entity: Dict) -> None:
    if "status" in entity and isinstance(entity["status"], str):
        entity["status"] = entity["status"].lower()

async def process_add_last_processed(entity: Dict) -> None:
    entity["last_processed_at"] = datetime.utcnow().isoformat() + "Z"