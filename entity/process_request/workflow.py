from datetime import datetime
import uuid
import httpx
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_process_request(entity):
    entity['status'] = 'processing'
    entity['createdAt'] = datetime.utcnow().isoformat() + "Z"
    entity['tempCorrelationId'] = str(uuid.uuid4())

    # Workflow orchestration
    await process_fetch_external_data(entity)
    await process_finalize(entity)

async def process_fetch_external_data(entity):
    try:
        headers = {"Accept": "application/json"}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get("https://icanhazdadjoke.com/", headers=headers)
            response.raise_for_status()
            data = response.json()
            entity['externalInfo'] = data.get("joke", "No joke found")
    except Exception as e:
        logger.exception("Failed to fetch external data")
        entity['status'] = 'failed'
        entity['error'] = str(e)

async def process_finalize(entity):
    if entity.get('status') != 'failed':
        entity['status'] = 'completed'
        entity['processedAt'] = datetime.utcnow().isoformat() + "Z"
    else:
        entity['processedAt'] = datetime.utcnow().isoformat() + "Z"