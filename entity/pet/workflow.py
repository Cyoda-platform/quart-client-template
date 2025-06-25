import logging
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

PETSTORE_BASE = "https://petstore3.swagger.io/api/v3"

async def process_fetch_pets(entity: dict):
    """Fetch pets from external API and update entity with results."""
    type_filter = entity.get("type")
    status_filter = entity.get("status") or "available"
    url = f"{PETSTORE_BASE}/pet/findByStatus"
    params = {"status": status_filter}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            pets = resp.json()
        except Exception as e:
            logger.exception(f"Failed fetching pets: {e}")
            entity["pets"] = []
            return
    if type_filter:
        pets = [pet for pet in pets if pet.get("category", {}).get("name", "").lower() == type_filter.lower()]
    entity["pets"] = pets

async def process_adopt_pet(entity: dict):
    """Mark a pet as adopted by updating external API and modifying entity status."""
    pet_id = entity.get("petId")
    if not isinstance(pet_id, int):
        entity["error"] = "Invalid or missing petId"
        return
    get_url = f"{PETSTORE_BASE}/pet/{pet_id}"
    update_url = f"{PETSTORE_BASE}/pet"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(get_url, timeout=10)
            resp.raise_for_status()
            pet = resp.json()
            if not pet:
                entity["error"] = f"Pet ID {pet_id} not found"
                return
            pet["status"] = "adopted"
            resp_update = await client.put(update_url, json=pet, timeout=10)
            resp_update.raise_for_status()
            entity["adopted"] = True
        except Exception as e:
            logger.exception(f"Failed to adopt pet {pet_id}: {e}")
            entity["error"] = "Failed to adopt pet"

async def process_normalize_pet(entity: dict):
    """Normalize pet status and category names to lowercase."""
    if "status" in entity and isinstance(entity["status"], str):
        entity["status"] = entity["status"].lower()
    if "category" in entity and isinstance(entity["category"], dict):
        if "name" in entity["category"] and isinstance(entity["category"]["name"], str):
            entity["category"]["name"] = entity["category"]["name"].lower()

async def process_pet(entity: dict):
    """Workflow orchestration for pet entity."""
    action = entity.get("action")
    if action == "fetch":
        await process_fetch_pets(entity)
    elif action == "adopt":
        await process_adopt_pet(entity)
    elif action == "normalize":
        await process_normalize_pet(entity)
    # No business logic here, just orchestration
    # Additional workflow steps can be added here if needed