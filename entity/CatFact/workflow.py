from dataclasses import dataclass

import logging

from datetime import datetime

from typing import Optional

import uuid

import httpx

from quart import Quart, jsonify

from quart_schema import QuartSchema, validate_request

from common.config.config import ENTITY_VERSION

from common.repository.cyoda.cyoda_init import init_cyoda

from app_init.app_init import cyoda_token, entity_service


CAT_FACT_API_URL = "https://catfact.ninja/fact"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

entity_job = {}  # Assuming this is global in this context


async def process_fetch_fact(entity: dict):
    """
    Fetch cat fact from external API and update entity with fact and fetchedAt timestamp.
    """
    fact = await fetch_cat_fact_from_api()
    if not fact:
        entity["error"] = "Failed to fetch cat fact"
        return False
    now_iso = datetime.utcnow().isoformat() + "Z"
    entity["fact"] = fact
    entity["fetchedAt"] = now_iso
    return True


async def process_update_job_status(entity: dict, status: str):
    """
    Update the job status in the global entity_job store if _jobId exists.
    """
    job_id = entity.get("_jobId")
    if not job_id:
        return
    requested_at = entity_job.get(job_id, {}).get("requestedAt") or datetime.utcnow().isoformat() + "Z"
    entity_job[job_id] = {"status": status, "requestedAt": requested_at}


async def fetch_cat_fact_from_api() -> Optional[str]:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(CAT_FACT_API_URL, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            fact = data.get("fact")
            if not fact:
                logger.error("No 'fact' field in Cat Fact API response")
                return None
            return fact
        except Exception as e:
            logger.exception(f"Failed to fetch cat fact from external API: {e}")
            return None