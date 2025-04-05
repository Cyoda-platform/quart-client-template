import asyncio
import httpx
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Business logic: set the processing start time.
async def process_set_started(entity: dict):
    entity["processingStartedAt"] = datetime.utcnow().isoformat()

# Business logic: perform the HTTP request and update the entity with the result.
async def process_fetch_result(entity: dict):
    # This function makes the asynchronous HTTP request.
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post("https://postman-echo.com/post", json={"query": entity["query"]})
        response.raise_for_status()
        result = response.json()
    entity["status"] = "completed"
    entity["result"] = result