import asyncio
import datetime
import logging
from dataclasses import dataclass
from typing import List, Dict

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# Data classes for request validation
@dataclass
class SubscribeRequest:
    email: str

@dataclass
class FetchScoresRequest:
    date: str = None  # Optional; if not provided, current date is used

@dataclass
class GamesQuery:
    page: int = 1
    limit: int = 10
    team: str = ""  # Optional filtering

# Async function to simulate sending an email.
async def send_email_notification(email: str, subject: str, body: str):
    logger.info(f"Sending email to {email} with subject '{subject}'")
    await asyncio.sleep(0.1)
    return True

# Workflow function for 'game' entity.
async def process_game(entity):
    # Example: annotate the game entity with processing timestamp.
    entity["processed_at"] = datetime.datetime.utcnow().isoformat()
    # Additional game-specific logic can be added here.
    return entity

# Workflow function for 'subscriber' entity.
async def process_subscriber(entity):
    # Example: annotate the subscriber entity with subscription timestamp.
    entity["subscribed_at"] = datetime.datetime.utcnow().isoformat()
    return entity

# New workflow function for 'notification' entity.
async def process_notification(entity):
    # Annotate notification entity with processing timestamp.
    entity["notified_at"] = datetime.datetime.utcnow().isoformat()
    subject = entity.get("subject", "")
    body = entity.get("body", "")
    try:
        subscribers = await entity_service.get_items(
            token=cyoda_token,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
        )
    except Exception as e:
        logger.exception(e)
        subscribers = []
    # Fire and forget sending email notifications to all subscribers.
    for subscriber in subscribers:
        email = subscriber.get("email")
        if email:
            asyncio.create_task(send_email_notification(email, subject, body))
    return entity

# Process scores by fetching from external API and storing each game via entity_service.
async def process_scores(date: str):
    api_key = "test"  # TODO: Replace with a secure configuration for the API key.
    url = f"https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key={api_key}"
    logger.info(f"Fetching NBA scores from external API for date {date} using URL: {url}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            external_data = response.json()
            logger.info(f"Fetched {len(external_data)} games for {date}")

            # For each game record, inject the date and persist with workflow.
            for game in external_data:
                game["date"] = date
                try:
                    await entity_service.add_item(
                        token=cyoda_token,
                        entity_model="game",
                        entity_version=ENTITY_VERSION,
                        entity=game,
                        workflow=process_game
                    )
                except Exception as e:
                    logger.exception(e)

            # Build notification data for daily scores.
            subject_line = f"Daily NBA Scores for {date}"
            body_content = f"Summary of games: {external_data}"
            notification_data = {
                "date": date,
                "games_summary": external_data,
                "subject": subject_line,
                "body": body_content,
            }
            # Persist notification entity with its workflow that sends emails.
            await entity_service.add_item(
                token=cyoda_token,
                entity_model="notification",
                entity_version=ENTITY_VERSION,
                entity=notification_data,
                workflow=process_notification
            )
    except httpx.HTTPError as e:
        logger.exception(e)
        raise Exception("Failed to fetch data from external API") from e

# Background scheduler to trigger fetch-scores daily at 6:00 PM UTC.
async def scheduler():
    while True:
        now = datetime.datetime.utcnow()
        target = now.replace(hour=18, minute=0, second=0, microsecond=0)
        if now >= target:
            target += datetime.timedelta(days=1)
        wait_seconds = (target - now).total_seconds()
        logger.info("Scheduler sleeping for %.2f seconds until next fetch", wait_seconds)
        await asyncio.sleep(wait_seconds)
        scheduled_date = target.strftime("%Y-%m-%d")
        logger.info("Scheduler triggering fetch-scores for date %s", scheduled_date)
        asyncio.create_task(process_scores(scheduled_date))

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    asyncio.create_task(scheduler())

# POST endpoint: Subscribe a user.
@app.route('/subscribe', methods=['POST'])
@validate_request(SubscribeRequest)
async def subscribe(data: SubscribeRequest):
    email = data.email
    if not email or not isinstance(email, str):
        return jsonify({"error": "Invalid email format."}), 400
    try:
        # Check if subscription already exists.
        existing = await entity_service.get_items_by_condition(
            token=cyoda_token,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
            condition={"email": email}
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Internal error while verifying subscription."}), 500

    if existing:
        return jsonify({"error": "Subscription already exists."}), 400

    try:
        subscriber_data = {"email": email}
        new_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
            entity=subscriber_data,
            workflow=process_subscriber
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to subscribe."}), 500

    logger.info(f"Subscribed new email: {email}")
    return jsonify({
        "message": "Subscription successful.",
        "data": {"id": new_id}
    }), 200

# GET endpoint: Retrieve all subscribers.
@app.route('/subscribers', methods=['GET'])
async def get_subscribers():
    try:
        subscribers = await entity_service.get_items(
            token=cyoda_token,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
        )
        return jsonify({"subscribers": subscribers}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve subscribers."}), 500

# POST endpoint: Trigger NBA scores fetching and notifications.
@app.route('/fetch-scores', methods=['POST'])
@validate_request(FetchScoresRequest)
async def fetch_scores(data: FetchScoresRequest):
    date = data.date if data.date else datetime.date.today().strftime("%Y-%m-%d")
    asyncio.create_task(process_scores(date))
    logger.info(f"Triggered fetch-scores process for date {date}")
    return jsonify({
        "message": "NBA scores fetch process has been initiated.",
        "date": date
    }), 200

# GET endpoint: Retrieve all games with query parameters.
@validate_querystring(GamesQuery)
@app.route('/games/all', methods=['GET'])
async def get_all_games():
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 10))
        team_filter = request.args.get("team")

        all_games = await entity_service.get_items(
            token=cyoda_token,
            entity_model="game",
            entity_version=ENTITY_VERSION,
        )

        if team_filter:
            all_games = [
                game for game in all_games
                if team_filter.lower() in game.get("homeTeam", "").lower() or 
                   team_filter.lower() in game.get("awayTeam", "").lower()
            ]
        
        total = len(all_games)
        start = (page - 1) * limit
        end = start + limit
        paginated_games = all_games[start:end]
        total_pages = (total + limit - 1) // limit

        return jsonify({
            "results": paginated_games,
            "pagination": {
                "currentPage": page,
                "totalPages": total_pages
            }
        }), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve games data."}), 500

# GET endpoint: Retrieve games by a specific date.
@app.route('/games/<date>', methods=['GET'])
async def get_games_by_date(date):
    try:
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError as ve:
            logger.exception(ve)
            return jsonify({"error": "Invalid date format. Please use YYYY-MM-DD."}), 400

        games = await entity_service.get_items_by_condition(
            token=cyoda_token,
            entity_model="game",
            entity_version=ENTITY_VERSION,
            condition={"date": date}
        )
        return jsonify({
            "date": date,
            "games": games
        }), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve game data for the specified date."}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)