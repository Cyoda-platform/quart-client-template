from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def call_external_api(name: str) -> dict:
    url = "https://api.agify.io"
    params = {"name": name}
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.exception(f"External API call failed: {e}")
        raise

async def process_validate_input(entity: dict):
    input_data = entity.get("inputData", {})
    name = input_data.get("name")
    if not name:
        raise ValueError("Missing 'name' in inputData")
    # Save extracted name for next steps
    entity["_name"] = name

async def process_call_external_api(entity: dict):
    name = entity.get("_name")
    result = await call_external_api(name)
    entity["_external_result"] = result

async def process_update_result(entity: dict):
    name = entity.get("_name")
    result = entity.get("_external_result", {})
    entity["status"] = "completed"
    entity["result"] = {
        "inputName": name,
        "predictedAge": result.get("age"),
        "count": result.get("count"),
        "processedAt": datetime.utcnow().isoformat() + "Z",
    }
    entity["completedAt"] = datetime.utcnow().isoformat() + "Z"
    entity["message"] = "Processing completed successfully"
    # clean up temp keys
    entity.pop("_name", None)
    entity.pop("_external_result", None)

async def process_handle_error(entity: dict, error: Exception):
    logger.exception(f"Error processing entity_jobs id={entity.get('id')}: {error}")
    entity["status"] = "failed"
    entity["message"] = str(error)
    # clean up temp keys
    entity.pop("_name", None)
    entity.pop("_external_result", None)

async def process_entity_jobs(entity: dict):
    try:
        await process_validate_input(entity)
        await process_call_external_api(entity)
        await process_update_result(entity)
    except Exception as e:
        await process_handle_error(entity, e)