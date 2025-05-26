import asyncio
import datetime
import logging
from typing import Dict, List

import httpx
from dataclasses import dataclass
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

async def process_game(entity: dict) -> dict:
    # Workflow orchestration only
    await process_compute_game_status(entity)
    await process_add_game_summary(entity)
    return entity

async def process_compute_game_status(entity: dict):
    home_score = entity.get("home_score")
    away_score = entity.get("away_score")

    if home_score is not None and away_score is not None:
        if home_score > away_score:
            entity["game_status"] = "home_win"
        elif away_score > home_score:
            entity["game_status"] = "away_win"
        else:
            entity["game_status"] = "draw"
    else:
        entity["game_status"] = "pending"

async def process_add_game_summary(entity: dict):
    summary = f"{entity.get('home_team','?')} {entity.get('home_score','?')} - {entity.get('away_team','?')} {entity.get('away_score','?')}"
    summary_entity = {
        "game_date": entity.get("date"),
        "summary": summary,
    }
    try:
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model="game_summary",
            entity_version=ENTITY_VERSION,
            entity=summary_entity,
            workflow=None  # no workflow for summary entity
        )
    except Exception as e:
        logger.warning(f"Failed to add game_summary entity: {e}")