from datetime import datetime
import logging
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

EXTERNAL_API_URL = "https://api.agify.io"

async def fetch_external_data(name: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:  # set reasonable timeout
        try:
            response = await client.get(EXTERNAL_API_URL, params={"name": name})
            response.raise_for_status()
            data = response.json()
            logger.info(f"Fetched external data for '{name}': {data}")
            return data
        except (httpx.HTTPError, httpx.RequestError) as e:
            logger.error(f"Failed to fetch external data for '{name}': {e}")
            return {"error": "Failed to fetch external data"}

async def process_validate_name(entity: dict):
    name = entity.get('name')
    if not name or not isinstance(name, str) or not name.strip():
        entity['status'] = 'failed'
        entity['result'] = {'error': 'Missing or invalid "name" attribute'}
        logger.error("process_validate_name: Missing or invalid 'name' attribute in entity")
        return False
    entity['name'] = name.strip()
    return True

async def process_enrich_external_data(entity: dict):
    name = entity['name']
    external_data = await fetch_external_data(name)
    if 'error' in external_data:
        entity['status'] = 'failed'
        entity['result'] = external_data
        logger.error(f"process_enrich_external_data: External API error for '{name}': {external_data['error']}")
        return False
    entity['result'] = {
        "inputName": name,
        "predictedAge": external_data.get("age"),
        "count": external_data.get("count"),
        "source": "agify.io"
    }
    return True

async def process_process_data(entity: dict):
    entity['status'] = 'processing'
    entity['requestedAt'] = datetime.utcnow().isoformat()

    if not await process_validate_name(entity):
        return

    if not await process_enrich_external_data(entity):
        return

    entity['status'] = 'completed'