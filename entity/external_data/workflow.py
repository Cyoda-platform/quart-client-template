import asyncio
from datetime import datetime
import aiohttp
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

# External API configuration
EXTERNAL_API_URL = "https://services.cro.ie/cws/companies"
AUTHORIZATION_HEADER = "Basic dGVzdEBjcm8uaWU6ZGEwOTNhMDQtYzlkNy00NmQ3LTljODMtOWM5Zjg2MzBkNWUw"

# Business logic functions (no workflow orchestration here)

def process_build_query_params(entity):
    # Build query parameters based on entity['params'] and attach them to the entity.
    params = entity.get("params", {})
    query_params = {
        "company_name": params.get("company_name", ""),
        "skip": str(params.get("skip", 0)),
        "max": str(params.get("max", 5)),
        "htmlEnc": "1"
    }
    entity["query_params"] = query_params

def process_build_headers(entity):
    # Build headers for the external API call and attach them to the entity.
    headers = {
        "accept": "application/json",
        "Authorization": AUTHORIZATION_HEADER
    }
    entity["headers"] = headers

async def process_fetch_external_data(entity):
    # Perform the external API request using the query parameters and headers stored in entity.
    async with aiohttp.ClientSession() as session:
        async with session.get(EXTERNAL_API_URL, params=entity.get("query_params"), headers=entity.get("headers")) as resp:
            if resp.status == 200:
                data = await resp.json()
                entity["data"] = data
                entity["status"] = "done"
                entity["completedAt"] = datetime.utcnow().isoformat()
            else:
                entity["status"] = "error"
                entity["error"] = f"External API returned status code {resp.status}"

def process_cleanup_entity(entity):
    # Remove temporary parameters used only for processing.
    entity.pop("params", None)
    entity.pop("query_params", None)
    entity.pop("headers", None)