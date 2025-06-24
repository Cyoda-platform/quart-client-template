from datetime import datetime
from typing import Dict, Any
import asyncio

class AppState:
    def __init__(self):
        self._lock = asyncio.Lock()
        self.adopted_pet_ids: set[str] = set()

    async def is_adopted(self, pet_id: str) -> bool:
        async with self._lock:
            return pet_id in self.adopted_pet_ids

app_state = AppState()

async def process_set_last_processed(entity: Dict[str, Any]):
    entity['last_processed'] = datetime.utcnow().isoformat() + 'Z'

async def process_set_description(entity: Dict[str, Any]):
    name = entity.get("name") or "Unknown"
    pet_type = entity.get("type") or "pet"
    entity['description'] = f"{name} is a lovely {pet_type}."

async def process_set_adopted_flag(entity: Dict[str, Any]):
    pet_id = entity.get("id")
    adopted = False
    if pet_id is not None:
        adopted = await app_state.is_adopted(str(pet_id))
    entity['adopted'] = adopted

async def process_pet(entity: Dict[str, Any]) -> Dict[str, Any]:
    # workflow orchestration (no business logic here)
    await process_set_last_processed(entity)
    await process_set_description(entity)
    await process_set_adopted_flag(entity)
    return entity