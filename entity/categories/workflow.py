from datetime import datetime
import asyncio
import aiohttp

# URL constants
SUPPLEMENTARY_API_URL = "https://api.practicesoftwaretesting.com/supplementary/info"
EXTERNAL_API_URL = "https://api.practicesoftwaretesting.com/categories/tree"

def process_add_timestamp(entity_data):
    # Append a UTC timestamp to mark processing time
    entity_data["processed_at"] = datetime.utcnow().isoformat() + "Z"
    return entity_data

async def process_fetch_supplementary(entity_data):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(SUPPLEMENTARY_API_URL, timeout=10) as resp:
                if resp.status == 200:
                    try:
                        supplementary = await resp.json()
                        entity_data["supplementary"] = supplementary
                    except Exception as json_exc:
                        entity_data["supplementary_error"] = f"JSON decode error: {json_exc}"
                else:
                    entity_data["supplementary_error"] = f"HTTP Error {resp.status}"
    except Exception as e:
        entity_data["supplementary_error"] = str(e)
    return entity_data