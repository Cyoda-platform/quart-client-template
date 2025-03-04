import asyncio
import logging
import datetime
import httpx

logger = logging.getLogger(__name__)

# Validate that necessary keys exist.
async def process_validate(entity: dict):
    if "externalParams" not in entity:
        raise ValueError("Missing externalParams in entity")
    if "operation" not in entity:
        raise ValueError("Missing operation in entity")
    if "inputData" not in entity:
        raise ValueError("Missing inputData in entity")

# Call the external API and update the entity with the external response.
async def process_external_api(entity: dict):
    async with httpx.AsyncClient() as client:
        external_url = "https://example.com/api"  # Replace with actual URL
        external_params = entity.get("externalParams", {})
        external_response = await client.post(external_url, json=external_params)
        try:
            external_data = external_response.json()
        except Exception as json_err:
            logger.error(f"Error parsing external API response: {json_err}")
            external_data = {}
        logger.info(f"External API responded with: {external_data}")
        entity["externalData"] = external_data

# Process a calculate_discount operation by applying a 10% discount.
async def process_calculate_discount(entity: dict):
    input_data = entity.get("inputData", {})
    value = input_data.get("value", 0)
    result = {
        "id": input_data.get("id"),
        "calculation": value * 0.9,
        "details": "10% discount applied."
    }
    entity["result"] = result

# Process operations not supported.
async def process_unsupported_operation(entity: dict):
    input_data = entity.get("inputData", {})
    operation = entity.get("operation")
    result = {
        "id": input_data.get("id"),
        "calculation": None,
        "details": f"Operation '{operation}' not supported."
    }
    entity["result"] = result

# Introduce a processing delay.
async def process_delay(entity: dict):
    await asyncio.sleep(1)

# Finalize processing by updating status and completion time.
async def process_finalize(entity: dict):
    entity["status"] = "completed"
    entity["completedAt"] = datetime.datetime.utcnow().isoformat()