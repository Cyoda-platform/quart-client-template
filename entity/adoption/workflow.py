import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_adoption_validate_cat_id(entity: dict):
    cat_id = entity.get("cat_id")
    if not cat_id:
        raise ValueError("cat_id is required in adoption entity")

async def process_adoption_check_cat_availability(entity: dict):
    cat_id = entity.get("cat_id")
    # TODO: Replace with actual async call to entity_service.get_item
    cat = await mock_get_cat(cat_id)  # Placeholder for entity_service.get_item
    if not cat:
        raise ValueError("Cat not found for adoption")
    if cat.get("state") != "Available":
        raise ValueError("Cat not available for adoption")
    # Attach cat data to entity for later use
    entity["_cat"] = cat

def process_adoption_set_status(entity: dict):
    entity["status"] = "Pending Approval"

def process_adoption_set_submitted_at(entity: dict):
    entity["submitted_at"] = datetime.utcnow().isoformat() + "Z"

def process_adoption_update_cat_state(entity: dict):
    cat = entity.get("_cat")
    if cat:
        cat["state"] = "Pending Adoption"
        # Persist cat state change by modifying cat dict directly
        # TODO: persist cat changes outside this function if needed

# Mock function for demonstration - replace with real entity_service call
async def mock_get_cat(cat_id: str) -> dict:
    # Example mock cat data
    return {"id": cat_id, "state": "Available"}