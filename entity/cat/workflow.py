import asyncio
import logging
from datetime import datetime
import httpx

CAT_API_BASE = "https://api.thecatapi.com/v1"
CAT_API_KEY = None  # TODO: Add your API key here if available
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def fetch_breed_info(breed_name: str):
    headers = {}
    if CAT_API_KEY:
        headers["x-api-key"] = CAT_API_KEY
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{CAT_API_BASE}/breeds/search?q={breed_name}", headers=headers)
            resp.raise_for_status()
            data = resp.json()
            if data:
                return data[0]
            return {}
        except Exception as e:
            logger.exception(f"Error fetching breed info for {breed_name}: {e}")
            return {}

async def process_cat_breed_info(entity: dict):
    breed_name = entity.get("breed", "")
    if breed_name:
        breed_info = await fetch_breed_info(breed_name)
        if breed_info:
            entity["breed_info"] = {
                "origin": breed_info.get("origin"),
                "temperament": breed_info.get("temperament"),
                "description": breed_info.get("description")
            }

def process_cat_set_default_state(entity: dict):
    if not entity.get("state"):
        entity["state"] = "Available"

def process_cat_validate_age(entity: dict):
    age = entity.get("age")
    if age is not None and (not isinstance(age, int) or age < 0):
        raise ValueError("Age must be a non-negative integer")