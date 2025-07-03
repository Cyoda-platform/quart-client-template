import logging
from datetime import datetime
from common.config.config import ENTITY_VERSION
from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

async def process_entity(entity: dict) -> dict:
    if "current_state" not in entity:
        entity["current_state"] = "Created"
    if "created_at" not in entity:
        entity["created_at"] = datetime.utcnow().isoformat()
    if "data" not in entity or not isinstance(entity["data"], dict):
        entity["data"] = {}
    return entity

async def is_valid_event(entity: dict) -> bool:
    trigger = entity.get('_workflow_trigger')
    if not trigger:
        return False
    event = trigger.get('event')
    return event == "predict_age"

async def is_unsupported_event(entity: dict) -> bool:
    trigger = entity.get('_workflow_trigger')
    if not trigger:
        return False
    event = trigger.get('event')
    return event != "predict_age"

async def is_valid_name(entity: dict) -> bool:
    trigger = entity.get('_workflow_trigger', {})
    payload = trigger.get('payload', {})
    name = payload.get("name")
    return bool(name and isinstance(name, str) and name.strip())

async def is_invalid_name(entity: dict) -> bool:
    valid = await is_valid_name(entity)
    return not valid

async def external_data_success(entity: dict) -> bool:
    data = entity.get("data", {})
    return "error" not in data

async def external_data_failure(entity: dict) -> bool:
    data = entity.get("data", {})
    return "error" in data

async def fail_workflow(entity: dict) -> dict:
    trigger = entity.get('_workflow_trigger', {})
    event = trigger.get('event', 'unknown')
    entity["current_state"] = "Failed"
    data = entity.get("data", {})
    if not data or "error" not in data:
        entity["data"] = {"error": f"Workflow failed for event '{event}'"}
    return entity

async def finish_processing(entity: dict) -> dict:
    # State transition to completed already done by workflow engine
    # Just ensure data exists
    if "data" not in entity or not isinstance(entity["data"], dict):
        entity["data"] = {}
    entity["current_state"] = "Completed"
    return entity