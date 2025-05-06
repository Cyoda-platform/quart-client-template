import logging
import httpx

logger = logging.getLogger(__name__)
PETSTORE_API_BASE = "https://petstore3.swagger.io/api/v3"

async def fetch_pet_from_external_api(entity):
    pet_id = entity.get("petId")
    url = f"{PETSTORE_API_BASE}/pet/{pet_id}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            entity["petId"] = data.get("id")
            entity["name"] = data.get("name")
            entity["category"] = data.get("category", {}).get("name") if data.get("category") else None
            entity["status"] = data.get("status")
            entity["photoUrls"] = data.get("photoUrls", [])
            entity.pop("errorMessage", None)
            entity["fetchError"] = None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                entity["fetchError"] = "Pet not found."
            else:
                logger.exception(f"HTTP error fetching pet {pet_id}")
                entity["fetchError"] = "Failed to fetch pet details."
        except Exception:
            logger.exception(f"Unexpected error fetching pet {pet_id}")
            entity["fetchError"] = "Unexpected error occurred."

async def process_validate_pet_id(entity):
    pet_id = entity.get("petId")
    if not isinstance(pet_id, int) or pet_id <= 0:
        entity["status"] = "error"
        entity["errorMessage"] = "Invalid or missing petId."
        return False
    return True

async def process_update_status(entity):
    if entity.get("fetchError"):
        entity["status"] = "error"
        entity["errorMessage"] = entity["fetchError"]
        entity.pop("fetchError", None)
    else:
        entity["status"] = "ready"
        entity.pop("errorMessage", None)