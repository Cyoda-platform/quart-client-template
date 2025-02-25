import asyncio
from datetime import datetime
import aiohttp

# Business logic: Fetch external data and store raw data in entity.
async def process_fetch_data(entity):
    external_url = "https://api.practicesoftwaretesting.com/brands"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(external_url, headers={"accept": "application/json"}) as resp:
                if resp.status != 200:
                    entity["status"] = "failed"
                    entity["error"] = f"Failed to fetch external data, HTTP status: {resp.status}"
                    entity["processedAt"] = datetime.utcnow().isoformat()
                    return entity
                raw_data = await resp.json()
    except Exception as e:
        entity["status"] = "failed"
        entity["error"] = f"Exception during external API call: {str(e)}"
        entity["processedAt"] = datetime.utcnow().isoformat()
        return entity
    entity["raw_data"] = raw_data
    return entity

# Business logic: Transform raw_data and update the entity.
async def process_transform_data(entity):
    try:
        # Example transformation: promote raw_data to data field.
        entity["data"] = entity.get("raw_data")
        entity["status"] = "completed"
        entity["processedAt"] = datetime.utcnow().isoformat()
    except Exception as e:
        entity["status"] = "failed"
        entity["error"] = f"Exception during processing: {str(e)}"
        entity["processedAt"] = datetime.utcnow().isoformat()
    return entity