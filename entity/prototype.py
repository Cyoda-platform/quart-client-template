from dataclasses import dataclass
import asyncio
import datetime
import logging
from typing import Dict, List

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request, validate_querystring

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory "databases"
_subscribers: List[str] = []
_games_by_date: Dict[str, List[Dict]] = {}
_entity_jobs: Dict[str, Dict] = {}

API_KEY = "test"
NBA_API_URL = "https://api.sportsdata.io/v3/nba/scores/json/ScoresBasicFinal/{date}?key=" + API_KEY

@dataclass
class FetchScoresParams:
    date: str

@dataclass
class SubscribeParams:
    email: str

@dataclass
class GamesAllQuery:
    page: int = 1
    limit: int = 100

async def fetch_scores_from_external_api(date: str) -> List[Dict]:
    url = NBA_API_URL.format(date=date)
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10.0)
            resp.raise_for_status()
            return resp.json()  # TODO: Confirm data format
        except (httpx.HTTPError, httpx.RequestError) as e:
            logger.exception(f"Failed fetching scores for {date}: {e}")
            return []

async def send_email_to_subscribers(date: str, games: List[Dict]):
    summary_lines = [f"{g.get('HomeTeam','N/A')} {g.get('HomeTeamScore','?')} - {g.get('AwayTeam','N/A')} {g.get('AwayTeamScore','?')}" for g in games]
    summary = f"NBA Scores for {date}:\n" + "\n".join(summary_lines)
    for email in _subscribers:
        logger.info(f"Sending email to {email}:\n{summary}")  # TODO: Implement real email sending

async def process_fetch_store_notify(job_id: str, date: str):
    logger.info(f"Job {job_id}: Starting fetch-store-notify for date {date}")
    _entity_jobs[job_id]["status"] = "processing"
    try:
        games = await fetch_scores_from_external_api(date)
        _games_by_date[date] = games
        if _subscribers and games:
            await send_email_to_subscribers(date, games)
        _entity_jobs[job_id]["status"] = "completed"
        logger.info(f"Job {job_id}: Completed successfully")
    except Exception as e:
        _entity_jobs[job_id]["status"] = "failed"
        logger.exception(f"Job {job_id}: Failed with exception: {e}")

@app.route("/fetch-scores", methods=["POST"])
@validate_request(FetchScoresParams)  # workaround: validation last for POST
async def fetch_scores(data: FetchScoresParams):
    date = data.date
    try:
        datetime.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"status":"error","message":"Invalid date format, expected YYYY-MM-DD"}),400
    job_id = f"job_{datetime.datetime.utcnow().isoformat()}"
    _entity_jobs[job_id] = {"status":"queued","requestedAt":datetime.datetime.utcnow().isoformat()}
    asyncio.create_task(process_fetch_store_notify(job_id, date))
    return jsonify({"status":"success","message":"Fetch started","job_id":job_id})

@app.route("/subscribe", methods=["POST"])
@validate_request(SubscribeParams)  # workaround: validation last for POST
async def subscribe(data: SubscribeParams):
    email = data.email
    if email not in _subscribers:
        _subscribers.append(email)
        logger.info(f"Added new subscriber: {email}")
    else:
        logger.info(f"Subscriber {email} already exists")
    return jsonify({"status":"success","message":"Subscription successful"})

@app.route("/subscribers", methods=["GET"])
async def get_subscribers():
    return jsonify({"subscribers":_subscribers})

@validate_querystring(GamesAllQuery)  # workaround: validation first for GET
@app.route("/games/all", methods=["GET"])
async def get_all_games(query: GamesAllQuery):
    page = query.page
    limit = query.limit
    all_games = [g for games in _games_by_date.values() for g in games]
    total = len(all_games)
    start = (page-1)*limit
    end = start+limit
    paged = all_games[start:end]
    return jsonify({
        "games":paged,
        "pagination":{"page":page,"limit":limit,"total":total,"total_pages":(total+limit-1)//limit if limit else 1}
    })

@app.route("/games/<date>", methods=["GET"])
async def get_games_by_date(date):
    try:
        datetime.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"status":"error","message":"Invalid date format, expected YYYY-MM-DD"}),400
    games = _games_by_date.get(date,[])
    return jsonify({"date":date,"games":games})

async def scheduled_daily_fetch():
    while True:
        now = datetime.datetime.utcnow()
        target = now.replace(hour=18,minute=0,second=0,microsecond=0)
        if now>=target:
            target+=datetime.timedelta(days=1)
        await asyncio.sleep((target-now).total_seconds())
        date_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        logger.info(f"Scheduled fetch triggered for date {date_str}")
        job_id = f"scheduled_job_{date_str}"
        _entity_jobs[job_id]={"status":"queued","requestedAt":datetime.datetime.utcnow().isoformat()}
        asyncio.create_task(process_fetch_store_notify(job_id, date_str))

@app.before_serving
async def startup():
    asyncio.create_task(scheduled_daily_fetch())

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)