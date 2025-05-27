from typing import Dict

async def process_fetch_nba_games(entity: Dict):
    # Fetch NBA games from external API and store raw data in entity
    import httpx
    from datetime import datetime

    NBA_API_BASE = "https://www.balldontlie.io/api/v1"
    today = datetime.utcnow().date().isoformat()
    url = f"{NBA_API_BASE}/games"
    params = {"dates[]": today, "per_page": 100}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        games = data.get("data", [])
        entity["fetched_games"] = games

async def process_transform_games(entity: Dict):
    # Transform raw fetched games into internal format and store in entity
    raw_games = entity.get("fetched_games", [])
    transformed = []
    for g in raw_games:
        transformed.append(
            {
                "gameId": str(g["id"]),
                "date": g["date"][:10],
                "homeTeam": g["home_team"]["full_name"],
                "awayTeam": g["visitor_team"]["full_name"],
                "homeScore": g["home_team_score"],
                "awayScore": g["visitor_team_score"],
                "status": g["status"].lower() if isinstance(g.get("status"), str) else g.get("status"),
            }
        )
    entity["games"] = transformed
    entity.pop("fetched_games", None)

async def process_notify_subscribers(entity: Dict):
    # Notify subscribers based on preferences and games
    import asyncio
    logger = entity.get("logger")
    subscribers = entity.get("subscribers", {})
    games = entity.get("games", [])
    tasks = []
    async def send_email_mock(email: str, subject: str, content: str):
        # TODO: Replace with real email sending logic
        if logger:
            logger.info(f"Sending email to {email} with subject '{subject}'")
        await asyncio.sleep(0.1)

    for email, sub in subscribers.items():
        pref_teams = sub.get("preferences", {}).get("favoriteTeams", [])
        relevant_games = [
            g for g in games
            if not pref_teams or g["homeTeam"] in pref_teams or g["awayTeam"] in pref_teams
        ]
        if not relevant_games:
            continue
        content_lines = [
            f"{g['awayTeam']} @ {g['homeTeam']} | {g['awayScore']} - {g['homeScore']} | {g['status']}"
            for g in relevant_games
        ]
        content = "\n".join(content_lines)
        subject = f"NBA Daily Scores - {entity.get('date', '')}"
        tasks.append(send_email_mock(email, subject, content))

    await asyncio.gather(*tasks)

async def process_games(entity: Dict):
    # Workflow orchestration only
    await process_fetch_nba_games(entity)
    await process_transform_games(entity)
    await process_notify_subscribers(entity)
    entity["status"] = "completed"
    entity["updatedAt"] = entity.get("updatedAt") or ""  # placeholder for updated timestamp