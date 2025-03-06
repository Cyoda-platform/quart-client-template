import asyncio
import datetime
import logging
from dataclasses import dataclass
from typing import List, Dict

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

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

# For GET requests with query parameters, note the decorator order workaround:
# Validation must be applied before route decorator.
@dataclass
class GamesQuery:
    page: int = 1
    limit: int = 10
    team: str = ""  # Optional filtering

# In-memory persistence mocks
subscribers: List[str] = []
games_storage: Dict[str, List[Dict]] = {}  # Key: date (YYYY-MM-DD), Value: list of game dicts

# TODO: Replace with proper external email service integration.
async def send_email_notification(email: str, subject: str, body: str):
    # This is a mock for sending an email.
    logger.info(f"Sending email to {email} with subject '{subject}'")
    # Simulate sending delay
    await asyncio.sleep(0.1)
    # TODO: Implement actual email-notification logic.
    return True

async def process_scores(date: str):
    api_key = "test"  # TODO: Replace with a secure configuration for the API key.
    url = f"https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key={api_key}"
    logger.info(f"Fetching NBA scores from external API for date {date} using URL: {url}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            external_data = response.json()
            # TODO: Validate and transform external_data as needed.
            # Save the data in the in-memory storage.
            games_storage[date] = external_data
            logger.info(f"Fetched and stored {len(external_data)} games for {date}")
            
            # Prepare email notification content
            subject = f"Daily NBA Scores for {date}"
            body = f"Summary of games: {external_data}"  # TODO: Format summary in a user-friendly way.
            
            # Fire and forget email notifications to all subscribers.
            for email in subscribers:
                asyncio.create_task(send_email_notification(email, subject, body))
    except httpx.HTTPError as e:
        logger.exception(e)
        raise Exception("Failed to fetch data from external API") from e

# POST endpoint: Subscribe a user
@app.route('/subscribe', methods=['POST'])  # Route decorator must go first for POST endpoints.
@validate_request(SubscribeRequest)         # Validation decorator follows.
async def subscribe(data: SubscribeRequest):
    email = data.email
    if not email or not isinstance(email, str):
        return jsonify({"error": "Invalid email format."}), 400
    if email in subscribers:
        return jsonify({"error": "Subscription already exists."}), 400

    subscribers.append(email)
    logger.info(f"Subscribed new email: {email}")
    return jsonify({
        "message": "Subscription successful.",
        "data": {"email": email}
    }), 200

# GET endpoint: Retrieve all subscribers (no validation needed)
@app.route('/subscribers', methods=['GET'])
async def get_subscribers():
    return jsonify({"subscribers": subscribers}), 200

# POST endpoint: Trigger NBA scores fetching and notifications
@app.route('/fetch-scores', methods=['POST'])  # Route decorator first for POST endpoints.
@validate_request(FetchScoresRequest)            # Validation decorator follows.
async def fetch_scores(data: FetchScoresRequest):
    date = data.date if data.date else datetime.date.today().strftime("%Y-%m-%d")
    # Fire and forget the processing task.
    asyncio.create_task(process_scores(date))
    logger.info(f"Triggered fetch-scores process for date {date}")
    return jsonify({
        "message": "NBA scores fetch process has been initiated.",
        "date": date
    }), 200

# GET endpoint: Retrieve all games with query parameters
@validate_querystring(GamesQuery)  # For GET endpoints, validation decorator goes first (workaround).
@app.route('/games/all', methods=['GET'])
async def get_all_games():
    try:
        # Access query parameters using standard approach
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 10))
        team_filter = request.args.get("team")

        # Aggregate all games
        all_games = []
        for date, games in games_storage.items():
            all_games.extend(games)

        # Apply simple filtering by team if provided.
        if team_filter:
            all_games = [
                game for game in all_games
                if team_filter.lower() in game.get("homeTeam", "").lower() or 
                   team_filter.lower() in game.get("awayTeam", "").lower()
            ]
        
        # Pagination logic
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

# GET endpoint: Retrieve games by a specific date (no query validation needed)
@app.route('/games/<date>', methods=['GET'])
async def get_games_by_date(date):
    try:
        # Validate date format (YYYY-MM-DD)
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError as ve:
            logger.exception(ve)
            return jsonify({"error": "Invalid date format. Please use YYYY-MM-DD."}), 400

        games = games_storage.get(date, [])
        return jsonify({
            "date": date,
            "games": games
        }), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Failed to retrieve game data for the specified date."}), 500

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)