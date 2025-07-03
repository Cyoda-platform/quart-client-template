import logging
from common.config.config import ENTITY_VERSION
from app_init.app_init import BeanFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

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
    if "data" not in entity or not isinstance(entity["data"], dict):
        entity["data"] = {}
    entity["current_state"] = "Completed"
    return entity

async def start_processing(entity: dict) -> dict:
    entity["current_state"] = "Processing"
    return entity

async def process_entity_workflow_trigger(entity: dict) -> dict:
    trigger = entity.pop('_workflow_trigger', None)
    if not trigger:
        return entity

    event = trigger.get("event")
    payload = trigger.get("payload", {})

    current_state = entity.get("current_state", "Created")

    try:
        if event == "predict_age":
            name = payload.get("name")
            if not name or not isinstance(name, str) or not name.strip():
                entity["current_state"] = "Failed"
                entity["data"] = {"error": "Missing or invalid 'name' in payload for predict_age event"}
                return entity

            entity = await start_processing(entity)
            from prototype import fetch_external_data
            external_result = await fetch_external_data(name.strip())

            entity["data"] = external_result

            if "error" in external_result:
                entity = await fail_workflow(entity)
            else:
                entity = await finish_processing(entity)
        else:
            entity["current_state"] = "Failed"
            entity["data"] = {"error": f"Unsupported event '{event}'"}

    except Exception as e:
        logger.exception(f"Error processing workflow event '{event}': {e}")
        entity["current_state"] = "Failed"
        entity["data"] = {"error": str(e)}

    return entity