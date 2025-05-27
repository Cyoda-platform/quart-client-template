Understood! We want to refactor the code by moving all async logic related to processing or side effects into the `process_{entity_name}` workflow functions, since these are invoked asynchronously before persistence of the entity.

Key points/reminders:
- Workflow functions get the entity dict as input, can modify it.
- They can call `entity_service` methods to get/add other entities of **different** models.
- They **cannot** add/update/delete entities of the same model to avoid infinite recursion.
- Workflow functions can perform asynchronous tasks (including fire and forget).
- This will keep the endpoint handlers simple and lean, offloading business logic to workflows.

---

### Refactoring plan:

1. **Subscriber entity workflow (`process_subscriber`)**  
   - Normalize email (lowercase) — already there.  
   - No other logic in subscribe endpoint except checking if subscriber exists. That check remains in endpoint as it's a query before add.  
   - No async side effects to move here.

2. **Entity job workflow (`process_entity_job`)**  
   - Job is created in fetch-scores endpoint, then fire-and-forget `process_fetch_scores` task is started.  
   - Move the entire `process_fetch_scores` logic *inside* `process_entity_job`.  
   - The workflow function will run asynchronously before saving the job entity, so we can perform all fetching, processing, storing games, sending emails inside it.  
   - Since this workflow is invoked **before** persisting the job entity, it can update other entities (games, subscribers).  
   - Since the job entity itself is being persisted, we only modify `entity` dict inside the workflow, no calls to add/update/delete the same entity model.  
   - We will remove the fire-and-forget task from the endpoint and just add the job entity (it will trigger the workflow).  
   - The workflow can update the state of the job entity via modifying the `entity` dict (e.g. `entity['status'] = ...`), and persist other entities (games, etc).

3. **Game entity workflow (`process_game`)**  
   - Currently no special async logic on game entity add, so keep it as pass-through.

---

### Implementation notes:

- We need to refactor `process_entity_job` to:
  - Mark status "processing"
  - Fetch NBA scores
  - Delete existing games of that date (using a different entity_model => allowed)
  - Add new games (different entity_model)
  - Send email notifications (get subscribers, fire emails)
  - Update job status to "completed" or "failed" by modifying `entity` dict (allowed)
  - Return the final modified entity dict to persist.

---

### Result

The endpoint `/fetch-scores` will just add the job entity with minimal fields and workflow `process_entity_job`. No fire-and-forget or manual updates needed.

---

### Here is the fully refactored code reflecting your request:

```python
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring
from dataclasses import dataclass

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# Entity names in underscore lowercase
entity_name_subscriber = "subscriber"
entity_name_game = "game"
entity_name_entity_job = "entity_job"

API_KEY = "test"
NBA_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=" + API_KEY

@dataclass
class SubscriptionRequest:
    email: str

@dataclass
class FetchScoresRequest:
    date: str

@dataclass
class GamesAllQuery:
    page: int = 1
    pageSize: int = 20
    startDate: Optional[str] = None
    endDate: Optional[str] = None

# -----------------------
# Workflow functions

async def process_subscriber(entity: Dict) -> Dict:
    # Normalize email to lowercase
    if 'email' in entity:
        entity['email'] = entity['email'].lower()
    return entity

async def process_game(entity: Dict) -> Dict:
    # No special processing for game currently
    return entity

async def process_entity_job(entity: Dict) -> Dict:
    """
    Workflow function for entity_job.
    Processes the job: fetch NBA scores, store games, send notifications,
    and update the job status inside the entity dict.
    """
    # Initial status update
    entity['status'] = "processing"
    entity['startedAt'] = datetime.utcnow().isoformat()

    date = entity.get('date')
    if not date:
        entity['status'] = "failed"
        entity['error'] = "Missing date field"
        return entity

    try:
        # Fetch NBA scores
        url = NBA_API_URL.format(date=date)
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            games = response.json()

        if not games:
            entity['status'] = "completed"
            entity['message'] = f"No games found for date {date}"
            return entity

        # Delete existing games for this date (different entity_model allowed)
        condition = {
            "cyoda": {
                "type": "group",
                "operator": "AND",
                "conditions": [
                    {
                        "jsonPath": "$.date",
                        "operatorType": "EQUALS",
                        "value": date,
                        "type": "simple"
                    }
                ]
            }
        }
        existing_games = await entity_service.get_items_by_condition(
            token=cyoda_auth_service,
            entity_model=entity_name_game,
            entity_version=ENTITY_VERSION,
            condition=condition,
        )
        for game in existing_games:
            tech_id = game.get("technical_id") or game.get("id")
            if tech_id is not None:
                try:
                    await entity_service.delete_item(
                        token=cyoda_auth_service,
                        entity_model=entity_name_game,
                        entity_version=ENTITY_VERSION,
                        technical_id=str(tech_id),
                        meta={},
                    )
                except Exception as e:
                    logger.warning(f"Failed to delete existing game {tech_id}: {e}")

        # Add new games with date and workflow to process_game
        for game in games:
            game_to_store = dict(game)
            game_to_store["date"] = date
            await entity_service.add_item(
                token=cyoda_auth_service,
                entity_model=entity_name_game,
                entity_version=ENTITY_VERSION,
                entity=game_to_store,
                workflow=process_game,
            )

        logger.info(f"Stored {len(games)} games for {date}")

        # Get subscribers to send notifications
        subscribers = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=entity_name_subscriber,
            entity_version=ENTITY_VERSION,
        )
        emails = [s.get("email") for s in subscribers if "email" in s]

        # Send email notifications (simulate by logging)
        if emails:
            summary_lines = []
            for game in games:
                home = game.get("HomeTeam", "N/A")
                away = game.get("AwayTeam", "N/A")
                home_score = game.get("HomeTeamScore", "N/A")
                away_score = game.get("AwayTeamScore", "N/A")
                summary_lines.append(f"{away} {away_score} @ {home} {home_score}")
            summary = "\n".join(summary_lines)
            for email in emails:
                # TODO: replace with real email sending logic
                logger.info(f"Sending NBA scores notification to {email} for {date}:\n{summary}")
        else:
            logger.info("No subscribers to notify.")

        entity['status'] = "completed"
        entity['completedAt'] = datetime.utcnow().isoformat()
        entity['message'] = f"Processed {len(games)} games for {date}"

    except Exception as e:
        logger.exception(f"Error processing NBA scores job for date {date}: {e}")
        entity['status'] = "failed"
        entity['error'] = str(e)
        entity['completedAt'] = datetime.utcnow().isoformat()

    return entity


# -----------------------
# Endpoints

@app.route("/subscribe", methods=["POST"])
@validate_request(SubscriptionRequest)
async def subscribe(data: SubscriptionRequest):
    email = data.email
    # Check if subscriber already exists
    condition = {
        "cyoda": {
            "type": "group",
            "operator": "AND",
            "conditions": [
                {
                    "jsonPath": "$.email",
                    "operatorType": "EQUALS",
                    "value": email.lower(),
                    "type": "simple"
                }
            ]
        }
    }
    existing_items = await entity_service.get_items_by_condition(
        token=cyoda_auth_service,
        entity_model=entity_name_subscriber,
        entity_version=ENTITY_VERSION,
        condition=condition,
    )
    if existing_items:
        logger.info(f"Subscriber already exists: {email}")
    else:
        data_dict = {"email": email}
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=entity_name_subscriber,
            entity_version=ENTITY_VERSION,
            entity=data_dict,
            workflow=process_subscriber,
        )
        logger.info(f"New subscriber added: {email}")
    return jsonify({"message": "Subscription successful", "email": email})

@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    items = await entity_service.get_items(
        token=cyoda_auth_service,
        entity_model=entity_name_subscriber,
        entity_version=ENTITY_VERSION,
    )
    emails = [item.get("email") for item in items if "email" in item]
    return jsonify({"subscribers": emails})

@validate_querystring(GamesAllQuery)
@app.route("/games/all", methods=["GET"])
async def get_all_games(query: GamesAllQuery):
    page = query.page
    page_size = query.pageSize
    start_date = query.startDate
    end_date = query.endDate

    all_games_full = await entity_service.get_items(
        token=cyoda_auth_service,
        entity_model=entity_name_game,
        entity_version=ENTITY_VERSION,
    )

    filtered_games = []
    for g in all_games_full:
        date_str = g.get("date")
        if date_str is None:
            continue
        if start_date and date_str < start_date:
            continue
        if end_date and date_str > end_date:
            continue
        filtered_games.append(g)

    total = len(filtered_games)
    total_pages = max((total + page_size - 1) // page_size, 1)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paged_games = filtered_games[start_idx:end_idx]

    return jsonify({
        "games": paged_games,
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "totalPages": total_pages,
            "totalGames": total,
        }
    })

@app.route("/games/<date>", methods=["GET"])
async def get_games_by_date(date: str):
    condition = {
        "cyoda": {
            "type": "group",
            "operator": "AND",
            "conditions": [
                {
                    "jsonPath": "$.date",
                    "operatorType": "EQUALS",
                    "value": date,
                    "type": "simple"
                }
            ]
        }
    }
    games = await entity_service.get_items_by_condition(
        token=cyoda_auth_service,
        entity_model=entity_name_game,
        entity_version=ENTITY_VERSION,
        condition=condition,
    )
    if not games:
        return jsonify({"date": date, "games": []})
    return jsonify({"date": date, "games": games})

@app.route("/fetch-scores", methods=["POST"])
@validate_request(FetchScoresRequest)
async def fetch_scores(data: FetchScoresRequest):
    date = data.date
    job_data = {
        "status": "queued",
        "requestedAt": datetime.utcnow().isoformat(),
        "date": date,
    }
    job_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model=entity_name_entity_job,
        entity_version=ENTITY_VERSION,
        entity=job_data,
        workflow=process_entity_job,  # Moved all processing inside this workflow
    )
    # No fire-and-forget task here, workflow handles everything
    return jsonify({
        "message": "Scores fetch job accepted",
        "jobId": str(job_id),
        "date": date
    })

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```

---

### What was moved into workflows?

- The entire async NBA scores fetching, deleting old games, adding new games, sending notification emails, and updating the job status was moved into `process_entity_job`.
- The `/fetch-scores` endpoint simply creates the job entity with minimal data and triggers the workflow.
- `process_subscriber` normalizes email.
- `process_game` remains simple, no extra logic currently.

---

This approach keeps endpoints minimal, moves business logic into the guaranteed-before-persist workflow functions, which can asynchronously modify entity state and manage related entities safely.

---

If you want me to help with adding real email sending or any other logic inside workflows, just ask!