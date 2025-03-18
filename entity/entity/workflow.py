import asyncio
import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

async def process_fetch_joke(entity: dict):
    # Call an external API to get a Chuck Norris joke and store the result in the entity.
    job_id = entity.get("job_id")
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.chucknorris.io/jokes/random")
        if response.status_code == 200:
            result = response.json().get("value", "No joke found.")
        else:
            result = "Error retrieving joke."
            logger.error(f"External API error for job_id {job_id}: {response.status_code}")
    entity["result"] = result

async def process_delay(entity: dict):
    # Simulate processing delay.
    await asyncio.sleep(1)

async def process_complete_status(entity: dict):
    # Update the entity status to completed and add a timestamp.
    completed_at = datetime.utcnow().isoformat() + "Z"
    entity["completedAt"] = completed_at
    entity["status"] = "completed"