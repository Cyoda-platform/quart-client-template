import asyncio
import datetime
import aiohttp

# Business logic: Validate trigger flag in the entity.
def process_validate_trigger(entity):
    if "trigger" in entity and entity["trigger"]:
        return True
    return False

# Business logic: Fetch external brand data and update the entity.
async def process_fetch_external_data(entity):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.practicesoftwaretesting.com/brands",
                headers={"accept": "application/json"}
            ) as response:
                if response.status != 200:
                    entity["error"] = f"External API returned status {response.status}."
                    return
                data = await response.json()
                entity["data"] = data
    except Exception as e:
        entity["error"] = f"Exception during external API fetch: {str(e)}"

# Business logic: Update the processed_at attribute.
def process_update_processed_at(entity):
    entity["processed_at"] = datetime.datetime.utcnow().isoformat()

# Business logic: Check if the entity has encountered an error.
def process_has_error(entity):
    return "error" in entity