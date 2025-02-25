import asyncio
import uuid
from datetime import datetime
import aiohttp

from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service
from common.config.config import ENTITY_VERSION

def process_set_unique_id(job: dict) -> dict:
    # Ensure a unique technical_id exists for the job.
    if "technical_id" not in job or not job["technical_id"]:
        job["technical_id"] = str(uuid.uuid4())
    return job

def process_add_workflow_timestamp(job: dict) -> dict:
    # Add workflow processing metadata.
    job["workflowProcessedAt"] = datetime.utcnow().isoformat()
    return job

def process_launch_background_task(job: dict) -> dict:
    # Launch the asynchronous background task using fire-and-forget pattern.
    try:
        asyncio.create_task(process_entity(job))
    except Exception as e:
        job["status"] = "failed"
        print(f"Failed to initiate background process for job {job['technical_id']}: {e}")
    return job

async def process_entity(job: dict) -> dict:
    # Process the entity by calling an external API and updating brands accordingly.
    external_api_url = "https://api.practicesoftwaretesting.com/brands"
    headers = {"accept": "application/json"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(external_api_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    existing_brands = await entity_service.get_items(
                        token=cyoda_token,
                        entity_model="brands",
                        entity_version=ENTITY_VERSION,
                    )
                    if existing_brands:
                        await entity_service.update_item(
                            token=cyoda_token,
                            entity_model="brands",
                            entity_version=ENTITY_VERSION,
                            entity=data,
                            meta={}
                        )
                    else:
                        await entity_service.add_item(
                            token=cyoda_token,
                            entity_model="brands",
                            entity_version=ENTITY_VERSION,
                            entity=data,
                            workflow=process_brands
                        )
                    job["status"] = "completed"
                else:
                    job["status"] = "failed"
    except Exception as e:
        job["status"] = "failed"
        print(f"Error processing job {job['technical_id']}: {e}")
    return job

def process_brands(entity: dict) -> dict:
    # Apply workflow to brands entity.
    entity["workflowProcessed"] = True
    entity["workflowProcessedAt"] = datetime.utcnow().isoformat()
    return entity