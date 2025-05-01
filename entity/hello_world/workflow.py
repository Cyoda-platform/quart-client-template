import logging
from datetime import datetime
from typing import Dict
import httpx

logger = logging.getLogger(__name__)

STATE_INITIALIZED = "initialized"
STATE_TRIGGERED = "triggered"
STATE_COMPLETED = "completed"
STATE_ERROR = "error"


async def process_initialize(entity: Dict) -> None:
    entity["workflowState"] = STATE_INITIALIZED
    entity["message"] = ""
    if "requestedAt" not in entity:
        entity["requestedAt"] = datetime.utcnow().isoformat() + "Z"
    logger.info(f"Entity {entity.get('entityId')} initialized")


async def process_trigger(entity: Dict) -> None:
    entity["workflowState"] = STATE_TRIGGERED


async def process_enrich_message(entity: Dict) -> None:
    custom_message = entity.get("customMessage", "Hello World")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get("https://api.quotable.io/random")
        response.raise_for_status()
        quote_data = response.json()
        quote = quote_data.get("content", "")
    final_message = f"{custom_message} — Quote: \"{quote}\""
    entity["message"] = final_message


async def process_complete(entity: Dict) -> None:
    entity["workflowState"] = STATE_COMPLETED
    entity["completedAt"] = datetime.utcnow().isoformat() + "Z"
    logger.info(f"Entity {entity.get('entityId')} processing completed")


async def process_error(entity: Dict, error: Exception) -> None:
    logger.exception(f"Error in process_hello_world workflow for entity {entity.get('entityId')}: {error}")
    entity["workflowState"] = STATE_ERROR
    entity["message"] = "Processing failed"