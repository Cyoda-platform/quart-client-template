#!/usr/bin/env python3
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service
import asyncio
import aiohttp
from datetime import datetime

# Business logic: set processed flags on the entity.
async def process_set_flags(entity):
    entity['processed'] = True
    entity['processed_at'] = datetime.utcnow().isoformat() + 'Z'

# Business logic: ensure the entity has a valid brands list.
async def process_initialize_brands(entity):
    if 'brands' not in entity or not isinstance(entity['brands'], list):
        entity['brands'] = []

# Business logic: fetch supplementary data and update the entity.
async def process_fetch_supplementary_data(entity):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://api.practicesoftwaretesting.com/supplementary',
                headers={'accept': 'application/json'},
                timeout=10
            ) as response:
                if response.status == 200:
                    supplementary_data = await response.json()
                    entity['supplementary'] = supplementary_data
                else:
                    print(f"process_fetch_supplementary_data: Received non-200 response: {response.status}")
    except Exception as e:
        print(f"process_fetch_supplementary_data: Error occurred: {e}")

# Business logic: perform additional asynchronous processing (fire and forget).
async def process_additional_processing(entity):
    try:
        await asyncio.sleep(0.1)
        # Additional processing logic can be added here.
    except Exception as e:
        print(f"process_additional_processing: Error occurred: {e}")