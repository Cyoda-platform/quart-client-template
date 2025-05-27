import logging
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_external_call(entity: dict):
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post("https://httpbin.org/post", json=entity)
        response.raise_for_status()

async def process_success(entity: dict):
    entity["status"] = "completed"
    entity["message"] = "Hello World"
    logger.info(f"Job {entity.get('job_id')} processed successfully in workflow.")

async def process_failure(entity: dict, error: Exception):
    entity["status"] = "failed"
    entity["message"] = None
    logger.exception(f"Job {entity.get('job_id')} failed in workflow: {error}")

async def process_entity_job(entity: dict):
    job_id = entity.get("job_id")
    if not job_id:
        logger.error("Job ID missing from entity in workflow.")
        entity["status"] = "failed"
        entity["message"] = "Missing job_id"
        return entity

    try:
        await process_external_call(entity)
        await process_success(entity)
    except Exception as e:
        await process_failure(entity, e)

    return entity