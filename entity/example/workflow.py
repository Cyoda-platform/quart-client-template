import httpx
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_fetch_pets(entity):
    filters = entity.get("filters", {})
    status = "available"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://petstore.swagger.io/v2/pet/findByStatus", params={"status": status})
            resp.raise_for_status()
            pets = resp.json()
    except Exception as e:
        logger.exception("Failed to fetch pets from external Petstore API")
        entity["status"] = "failed"
        entity["error"] = str(e)
        return

    filtered = []
    for pet in pets:
        pet_type = pet.get("category", {}).get("name", "").lower()
        if filters.get("type") and filters["type"].lower() != pet_type:
            continue
        filtered.append({
            "id": str(pet.get("id")),
            "name": pet.get("name", ""),
            "type": pet_type,
            "breed": "unknown",
            "age": -1,
            "description": pet.get("status", ""),
            "imageUrl": pet.get("photoUrls")[0] if pet.get("photoUrls") else "",
        })
    entity["pets"] = filtered
    entity["status"] = "completed"

async def process_mark_favorite(entity):
    pet_id = entity.get("petId")
    if not pet_id:
        entity["success"] = False
        entity["message"] = "petId is required"
        return
    favorites = entity.setdefault("favorites_store", set())
    favorites.add(pet_id)
    entity["success"] = True
    entity["message"] = "Pet added to favorites."

async def process_list_favorites(entity):
    favorites = entity.get("favorites_store", set())
    pets = [{"id": pid, "name": f"Pet {pid}", "type": "unknown", "breed": "unknown", "age": -1, "imageUrl": ""} for pid in favorites]
    entity["favorites"] = pets

async def my_workflow(entity):
    action = entity.get("action")
    if action == "search":
        await process_fetch_pets(entity)
    elif action == "favorite":
        await process_mark_favorite(entity)
    elif action == "list_favorites":
        await process_list_favorites(entity)
    else:
        entity["error"] = "Unknown action"
        entity["status"] = "failed"