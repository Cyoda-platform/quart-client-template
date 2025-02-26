import aiohttp
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

# Fetch external data and store the result in the entity.
async def process_fetch_external_data(entity: dict):
    external_url = (
        "https://api.sportsdata.io/v3/nba/scores/ScoresBasic/2020-SEP-01"
        "?key=YOUR_API_KEY"  # TODO: Replace with an actual API key.
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(external_url) as response:
                # Even if we fetch external data, we simulate a result below.
                await response.json()
    except Exception as e:
        print(f"Error fetching data from external API in process_fetch_external_data: {e}")
    
    # Simulate external data result.
    entity["external_data"] = {
        "updatedGames": [
            {
                "gameId": "1234",
                "homeTeam": "Team A",
                "awayTeam": "Team B",
                "homeScore": 101,
                "awayScore": 99,
                "timeRemaining": "02:15"
            }
        ]
    }

# Update the score entity using the external data.
async def process_update_score_entity(entity: dict):
    try:
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="score",
            entity_version=ENTITY_VERSION,
            entity=entity.get("external_data"),
            meta={"technical_id": "latest"}
        )
    except Exception as e:
        print(f"Error updating score entity in process_update_score_entity: {e}")

# Retrieve subscribers and store them in the entity.
async def process_get_subscribers(entity: dict):
    try:
        subscribers = await entity_service.get_items(
            token=cyoda_token,
            entity_model="subscriber",
            entity_version=ENTITY_VERSION,
        )
        entity["subscribers"] = subscribers
    except Exception as e:
        print(f"Error retrieving subscribers in process_get_subscribers: {e}")
        entity["subscribers"] = []

# Notify each subscriber with the external data.
async def process_notify_subscribers(entity: dict):
    result = entity.get("external_data", {})
    subscribers = entity.get("subscribers", [])
    for sub in subscribers:
        try:
            print(f"Notify subscriber at {sub.get('callbackUrl')} with data: {result}")
            # In production, perform an asynchronous POST to sub['callbackUrl'].
        except Exception as e:
            print(f"Error notifying subscriber {sub.get('callbackUrl')}: {e}")

# Mark the job entity as completed by modifying its state.
async def process_mark_completed(entity: dict):
    trigger_time = entity.get("triggerTime", "unknown")
    entity["status"] = "completed"
    entity["processedAt"] = trigger_time