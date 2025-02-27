import datetime
import asyncio

# Business logic function: Add processed timestamp to the entity.
async def process_add_timestamp(entity):
    entity["processedAt"] = datetime.datetime.utcnow().isoformat()

# Business logic function: Asynchronously fetch and add supplementary information to the entity.
async def process_add_supplementary_info(entity):
    try:
        await asyncio.sleep(0.1)  # Simulate asynchronous I/O delay.
        name = entity.get("name", "unknown")
        supplementary_data = {"info": f"Additional details based on {name}"}
        entity["supplementaryInfo"] = supplementary_data
    except Exception as e:
        print(f"Error fetching supplementary info: {e}")
        entity["supplementaryInfo"] = {}