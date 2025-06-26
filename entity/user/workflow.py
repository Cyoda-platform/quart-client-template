from fastapi import HTTPException
import asyncio

async def async_fetch_profile(user_id: str) -> dict:
    # TODO: Implement actual async profile fetch logic
    await asyncio.sleep(0.1)
    return {"name": "Mock User", "id": user_id}

async def async_send_welcome_email(email: str):
    # TODO: Implement actual async email sending logic
    await asyncio.sleep(0.1)

async def enrich_profile(entity: dict):
    if 'id' in entity:
        entity['profile'] = await async_fetch_profile(entity['id'])

async def send_welcome_email_if_new(entity: dict):
    if not entity.get('created'):
        await async_send_welcome_email(entity.get('email', ''))
        entity['created'] = True

async def process_user(entity: dict):
    # Workflow orchestration only
    await enrich_profile(entity)
    await send_welcome_email_if_new(entity)