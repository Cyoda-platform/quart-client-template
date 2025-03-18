import asyncio
import logging
from datetime import datetime

import httpx

# Initialize logger
logger = logging.getLogger(__name__)

# Process function to fetch current UTC time and update entity.
async def process_fetch_time(entity: dict):
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get("http://worldtimeapi.org/api/timezone/Etc/UTC")
        response.raise_for_status()
        time_data = response.json()
        utc_time = time_data.get("utc_datetime", datetime.utcnow().isoformat())
    entity["requestedAt"] = utc_time

# Process function to simulate processing delay.
async def process_delay(entity: dict):
    await asyncio.sleep(2)

# Process function to fetch a joke and update entity.
async def process_fetch_joke(entity: dict):
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get("https://api.chucknorris.io/jokes/random")
        response.raise_for_status()
        joke_data = response.json()
    entity["joke"] = joke_data.get("value", "No joke available")

# Process function to mark entity as completed.
async def process_mark_complete(entity: dict):
    entity["status"] = "completed"
    entity["completedAt"] = datetime.utcnow().isoformat()