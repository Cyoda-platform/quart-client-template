from datetime import datetime
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_fetch_weather_data(entity: dict):
    """Fetch weather data from external API and update entity result."""
    weather_data = await fetch_weather_data(
        entity["latitude"],
        entity["longitude"],
        entity["parameters"],
        entity["start_date"],
        entity["end_date"],
    )
    entity["result"] = {
        "latitude": entity["latitude"],
        "longitude": entity["longitude"],
        "parameters": weather_data.get("hourly", {}),
        "start_date": entity["start_date"],
        "end_date": entity["end_date"],
        "fetched_at": datetime.utcnow().isoformat() + "Z",
    }

async def process_weather_fetch_job(entity: dict):
    """Workflow orchestration for weather_fetch_job entity."""
    entity.setdefault("created_at", datetime.utcnow().isoformat() + "Z")
    entity["status"] = "processing"
    try:
        entity["status"] = "fetching"
        await process_fetch_weather_data(entity)
        entity["status"] = "completed"
        entity.pop("error", None)
    except Exception as e:
        logger.exception("Weather fetch failed in workflow")
        entity["status"] = "failed"
        entity["error"] = str(e)
        entity.pop("result", None)
    return entity