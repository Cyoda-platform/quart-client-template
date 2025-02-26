from datetime import datetime
import aiohttp
import asyncio

# process_companies is the only function that orchestrates the workflow
async def process_companies(entity):
    try:
        await process_add_timestamp(entity)
        await process_validate_entity(entity)
        # If validation failed, exit workflow.
        if entity.get("status") == "failed":
            return entity
        await process_build_api_parameters(entity)
        await process_call_external_api(entity)
    except Exception as e:
        entity["status"] = "failed"
        entity["data"] = {"error": str(e)}
    return entity

# Adds a timestamp indicating when processing started.
async def process_add_timestamp(entity):
    entity["preProcessedAt"] = datetime.utcnow().isoformat()

# Validates that the entity contains a company name; 
# if missing, updates the entity to a failed state.
async def process_validate_entity(entity):
    company_name = entity.get("companyName")
    if not company_name:
        entity["status"] = "failed"
        entity["data"] = {"error": "Missing company name parameter."}

# Builds the external API URL and headers based on the entity parameters.
async def process_build_api_parameters(entity):
    company_name = entity.get("companyName")
    skip = entity.get("skip", 0)
    max_records = entity.get("max", 5)
    url = (
        f"https://services.cro.ie/cws/companies?&company_name={company_name}"
        f"&skip={skip}&max={max_records}&htmlEnc=1"
    )
    headers = {
        "accept": "application/json",
        "Authorization": "Basic dGVzdEBjcm8uaWU6ZGEwOTNhMDQtYzlkNy00NmQ3LTljODMtOWM5Zjg2MzBkNWUw"
    }
    entity["url"] = url
    entity["headers"] = headers

# Calls the external API and updates the entity based on the response.
async def process_call_external_api(entity):
    async with aiohttp.ClientSession() as session:
        async with session.get(entity["url"], headers=entity["headers"]) as response:
            if response.status != 200:
                entity["status"] = "failed"
                entity["data"] = {"error": f"External API returned status {response.status}"}
                return
            external_data = await response.json()
            entity["status"] = "completed"
            entity["data"] = external_data