```python
import asyncio
import logging
from datetime import datetime
from typing import List, Dict

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory mock storage
subscribers: set = set()
games_storage: Dict[str, List[dict]] = {}

# External NBA Scores API config
API_KEY = "test"  # Provided key in requirements
API_ENDPOINT = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key={key}"


@app.route("/subscribe", methods=["POST"])
async def subscribe():
    try:
        data = await request.get_json()
        email = data.get("email")
        if not email or "@" not in email:
            return jsonify({"message": "Invalid email"}), 400

        if email in subscribers:
            return jsonify({"message": "Email already subscribed", "email": email}), 200

        subscribers.add(email)
        logger.info(f"New subscriber added: {email}")
        return jsonify({"message": "Subscription successful", "email": email}), 201

    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal server error"}), 500


@app.route("/scores/fetch", methods=["POST"])
async def fetch_scores():
    try:
        data = await request.get_json()
        date_str = data.get("date")
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        except Exception:
            return jsonify({"message": "Invalid date format, expected YYYY-MM-DD"}), 400

        job_id = f"fetch_scores_{date_str}_{datetime.utcnow().isoformat()}"
        entity_job = {job_id: {"status": "processing", "requestedAt": datetime.utcnow().isoformat()}}
        # Fire and forget processing task
        asyncio.create_task(process_scores(entity_job, date_str))
        return jsonify({"message": "Scores fetch started", "job_id": job_id}), 202

    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal server error"}), 500


async def process_scores(entity_job: dict, date_str: str):
    try:
        url = API_ENDPOINT.format(date=date_str, key=API_KEY)
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                logger.error(f"Failed to fetch data from external API: {resp.status_code} {resp.text}")
                entity_job[list(entity_job.keys())[0]]["status"] = "failed"
                return

            games = resp.json()
            # Store games (replace existing for the date)
            # Structure games data to minimal required fields
            filtered_games = []
            for game in games:
                # Example fields, can be adapted if data changes
                filtered_game = {
                    "date": date_str,
                    "home_team": game.get("HomeTeam"),
                    "away_team": game.get("AwayTeam"),
                    "home_score": game.get("HomeTeamScore"),
                    "away_score": game.get("AwayTeamScore"),
                    "status": game.get("Status"),
                    # TODO: Add more fields if needed
                }
                filtered_games.append(filtered_game)

            games_storage[date_str] = filtered_games
            logger.info(f"Stored {len(filtered_games)} games for {date_str}")

            # Send notifications
            await notify_subscribers(date_str, filtered_games)
            entity_job[list(entity_job.keys())[0]]["status"] = "completed"
            logger.info(f"Completed processing scores for {date_str}")

    except Exception as e:
        logger.exception(e)
        entity_job[list(entity_job.keys())[0]]["status"] = "failed"


async def notify_subscribers(date_str: str, games: List[dict]):
    # Compose summary email content
    if not subscribers:
        logger.info("No subscribers to notify")
        return

    summary_lines = [f"NBA Scores for {date_str}:\n"]
    for g in games:
        line = f"{g['away_team']} {g['away_score']} @ {g['home_team']} {g['home_score']} - Status: {g['status']}"
        summary_lines.append(line)
    summary = "\n".join(summary_lines)

    # TODO: Replace this mock with real email sending logic
    for email in subscribers:
        logger.info(f"Sending notification to {email}:\n{summary}")
        # Simulate async email send with asyncio.sleep
        await asyncio.sleep(0.01)
    logger.info(f"Notifications sent to {len(subscribers)} subscribers")


@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    return jsonify({"subscribers": list(subscribers)}), 200


@app.route("/games/all", methods=["GET"])
async def get_all_games():
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 20))
        all_games = []
        for games_list in games_storage.values():
            all_games.extend(games_list)

        # Simple pagination
        total = len(all_games)
        start = (page - 1) * limit
        end = start + limit
        paged_games = all_games[start:end]

        return jsonify({
            "games": paged_games,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total
            }
        }), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal server error"}), 500


@app.route("/games/<date_str>", methods=["GET"])
async def get_games_by_date(date_str):
    try:
        # Validate date format
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except Exception:
            return jsonify({"message": "Invalid date format, expected YYYY-MM-DD"}), 400

        games = games_storage.get(date_str, [])
        return jsonify({
            "date": date_str,
            "games": games
        }), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"message": "Internal server error"}), 500


if __name__ == '__main__':
    import sys
    import logging.config

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )

    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
```