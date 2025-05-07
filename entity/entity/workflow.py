from typing import Dict, Any

import asyncio
import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

EXTERNAL_API_URL = "https://jsonplaceholder.typicode.com/todos/1"


async def fetch_external_data() -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(EXTERNAL_API_URL)
            response.raise_for_status()
            data = response.json()
            logger.info("Fetched external data successfully")
            return data
        except httpx.HTTPError as e:
            logger.exception(f"Failed to fetch external data: {e}")
            return {}


async def process_trigger_workflow(entity: Dict[str, Any]) -> None:
    event_type = entity.get('event_type')
    payload = entity.get('payload', {})

    external_data = await fetch_external_data()

    processed_result = {
        "hello_message": "Hello World!",
        "event_type": event_type,
        "payload_received": payload,
        "external_data": external_data,
        "processed_at": datetime.utcnow().isoformat() + "Z",
    }

    entity['result'] = processed_result
    entity['current_state'] = "completed"


async def process_process_data(entity: Dict[str, Any]) -> None:
    input_data = entity.get('input_data', {})

    external_result = await fetch_external_data()

    result = {
        "calculation_result": external_result,
        "input_data_received": input_data,
        "processed_at": datetime.utcnow().isoformat() + "Z",
    }

    entity['result'] = result
    entity['current_state'] = "data_processed"