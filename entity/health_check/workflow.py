import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_health_check_validate_cat_id(entity: dict):
    cat_id = entity.get("cat_id")
    if not cat_id:
        raise ValueError("cat_id is required in health_check entity")

async def process_health_check_get_cat(entity: dict) -> dict:
    cat_id = entity.get("cat_id")
    # TODO: Replace with actual async call to entity_service.get_item
    cat = await mock_get_cat(cat_id)  # Placeholder for entity_service.get_item
    if not cat:
        raise ValueError("Cat not found for health check")
    return cat

def process_health_check_update_cat_state(entity: dict, cat: dict):
    health_status = entity.get("health_status", "").lower()
    if health_status != "healthy":
        cat["state"] = "Unavailable"
    else:
        if cat.get("state") == "Unavailable":
            cat["state"] = "Available"
    # Persist cat state change by modifying cat dict directly
    # TODO: persist cat changes outside this function if needed

# Mock function for demonstration - replace with real entity_service call
async def mock_get_cat(cat_id: str) -> dict:
    # Example mock cat data
    return {"id": cat_id, "state": "Available"}