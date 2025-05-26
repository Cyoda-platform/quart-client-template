import asyncio
import datetime
import logging
from typing import Dict, List

import httpx
from dataclasses import dataclass
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

API_KEY = "test"
EXTERNAL_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key={key}"

async def process_fetch_scores(entity: dict):
    date = entity.get("date")
    if not date:
        entity["status"] = "failed"
        entity["error"] = "Missing date"
        return
    url = EXTERNAL_API_URL.format(date=date, key=API_KEY)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            entity["fetched_games"] = []
            if isinstance(data, list):
                for g in data:
                    entity["fetched_games"].append({
                        "date": date,
                        "home_team": g.get("HomeTeam"),
                        "away_team": g.get("AwayTeam"),
                        "home_score": g.get("HomeTeamScore"),
                        "away_score": g.get("AwayTeamScore"),
                    })
            else:
                entity["fetched_games"] = []
            entity["status"] = "fetched"
    except Exception as e:
        logger.exception(e)
        entity["status"] = "failed"
        entity["error"] = str(e)

async def process_notify(entity: dict):
    date = entity.get("date")
    subscribers = entity.get("subscribers", [])
    games = entity.get("games", [])
    if not subscribers or not games:
        entity["notification_status"] = "no subscribers or no games"
        return
    summary_lines = []
    for game in games:
        summary_lines.append(
            f"{game.get('home_team','?')} {game.get('home_score','?')} - "
            f"{game.get('away_team','?')} {game.get('away_score','?')}"
        )
    summary = "\n".join(summary_lines) or "No games found."
    for email in subscribers:
        logger.info(f"Sending email to {email} for {date}:\n{summary}")
    await asyncio.sleep(0.1)
    entity["notification_status"] = "sent"

async def process_subscribe(entity: dict):
    email = entity.get("email")
    if email:
        entity["email"] = email.strip().lower()
    entity["subscribed"] = True

async def process_subscriber(entity: dict):
    state = entity.get("state")
    if state == "subscribe":
        await process_subscribe(entity)
        entity["state"] = "subscribed"
    elif state == "fetch_scores":
        await process_fetch_scores(entity)
        entity["state"] = "scores_fetched" if entity.get("status") == "fetched" else "failed"
    elif state == "notify":
        await process_notify(entity)
        entity["state"] = "notified"
    else:
        entity["state"] = "unknown_state"
```