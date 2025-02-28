import asyncio
import datetime
import uuid
import aiohttp
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

SPORTS_DATA_API_KEY = "f8824354d80d45368063dd2e6fb16c38"
SPORTS_DATA_URL_TEMPLATE = "https://api.sportsdata.io/v3/scores/json/GamesByDate/{date}?key=" + SPORTS_DATA_API_KEY

# Business logic for workflow on a score entity.
async def process_scores_workflow(entity):
    entity["workflowProcessed"] = True
    entity["workflowProcessedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
    return entity

# Business logic: mark the job as processed.
def process_mark_as_processed(entity):
    entity["workflowProcessed"] = True
    entity["workflowProcessedAt"] = datetime.datetime.utcnow().isoformat() + "Z"

# Business logic: ensure the job has a valid identifier.
def process_assign_job_id(entity):
    job_id = entity.get("technical_id") or entity.get("id")
    if not job_id:
        job_id = str(uuid.uuid4())
        entity["technical_id"] = job_id

# Workflow orchestration: launch background task if job has a date.
def process_launch_background_task(entity):
    if entity.get("date"):
        try:
            asyncio.create_task(process_scores(entity))
        except Exception as e:
            print(f"Error launching background processing for job {entity.get('technical_id')}: {e}")
    else:
        print(f"Job {entity.get('technical_id')} missing 'date' field; background processing will not be launched.")

# Asynchronous business logic: fetch external scores using the date from the job entity.
async def process_fetch_external_data(entity):
    date = entity.get("date")
    url = SPORTS_DATA_URL_TEMPLATE.format(date=date)
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                data = await response.json()
                return data
        except Exception as e:
            print(f"Error fetching data from external API for date {date}: {e}")
            return None

# Business logic: mark job as failed.
async def process_handle_external_failure(entity):
    entity["status"] = "failed"
    entity["failedAt"] = datetime.datetime.utcnow().isoformat() + "Z"

# Business logic: update or add a score record for a single game.
async def process_update_or_add_score(game):
    game_id = game.get("GameID") or str(uuid.uuid4())
    try:
        existing = await entity_service.get_item(
            token=cyoda_token,
            entity_model="scores",
            entity_version=ENTITY_VERSION,
            technical_id=game_id
        )
    except Exception:
        existing = None

    if (not existing) or (existing.get("finalScore") != game.get("FinalScore")):
        score_data = {
            "gameId": game_id,
            "homeTeam": game.get("HomeTeam"),
            "awayTeam": game.get("AwayTeam"),
            "quarterScores": game.get("QuarterScores", []),
            "finalScore": game.get("FinalScore"),
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        }
        if existing:
            try:
                await entity_service.update_item(
                    token=cyoda_token,
                    entity_model="scores",
                    entity_version=ENTITY_VERSION,
                    entity=score_data,
                    meta={}
                )
            except Exception as e:
                print(f"Error updating score for game {game_id}: {e}")
        else:
            try:
                await entity_service.add_item(
                    token=cyoda_token,
                    entity_model="scores",
                    entity_version=ENTITY_VERSION,
                    entity=score_data,
                    workflow=process_scores_workflow
                )
            except Exception as e:
                print(f"Error adding score for game {game_id}: {e}")
        return score_data
    return None

# Business logic: process scores for the job.
async def process_scores(entity):
    external_data = await process_fetch_external_data(entity)
    if external_data is None:
        await process_handle_external_failure(entity)
        return entity

    updated_games = []
    for game in external_data:
        result = await process_update_or_add_score(game)
        if result:
            updated_games.append(result)

    entity["status"] = "completed"
    entity["completedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
    if updated_games:
        print(f"Job {entity.get('technical_id')} - Updated games: {updated_games}")
    return entity