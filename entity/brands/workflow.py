import asyncio
import datetime
import aiohttp

# Business logic: fetching supplementary data from external API.
async def process_fetch_supplementary(entity_data):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.example.com/supplementary_data", 
                                   timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    supplementary = await resp.json()
                    entity_data["supplementary"] = supplementary
                else:
                    entity_data["supplementary_error"] = f"Unexpected status: {resp.status}"
    except Exception as err:
        entity_data["supplementary_error"] = str(err)

# Business logic: adding metadata information.
def process_add_metadata(entity_data):
    entity_data["processedAt"] = datetime.datetime.utcnow().isoformat()