from datetime import datetime, timedelta, time
import asyncio
import logging
import httpx

EGG_COOK_TIMES = {"soft": 4, "medium": 7, "hard": 12}

async def fetch_current_utc():
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("http://worldtimeapi.org/api/timezone/Etc/UTC")
            r.raise_for_status()
            data = r.json()
            current_time_iso = data.get("utc_datetime")
            return datetime.fromisoformat(current_time_iso.replace("Z", "+00:00"))
    except Exception:
        logging.exception("Failed to fetch current time from external API")
        return datetime.utcnow()

async def process_calculate_set_time(entity: dict):
    egg_type = entity.get("egg_type")
    custom_time_str = entity.get("custom_time")

    current_utc = await fetch_current_utc()

    if custom_time_str:
        try:
            hour, minute = map(int, custom_time_str.split(":"))
            alarm_time_candidate = datetime.combine(current_utc.date(), time(hour, minute))
            if alarm_time_candidate <= current_utc:
                alarm_time_candidate += timedelta(days=1)
            entity["set_time"] = alarm_time_candidate.isoformat()
        except Exception:
            raise ValueError("Invalid custom_time format, expected HH:MM")
    else:
        set_time = current_utc + timedelta(minutes=EGG_COOK_TIMES[egg_type])
        entity["set_time"] = set_time.isoformat()

async def process_clean_entity(entity: dict):
    # Remove custom_time from entity if exists
    if "custom_time" in entity:
        del entity["custom_time"]

async def process_set_status(entity: dict):
    entity["status"] = "created"

async def process_alarm(entity: dict):
    # Workflow orchestration only, no business logic here
    egg_type = entity.get("egg_type")
    if egg_type not in EGG_COOK_TIMES:
        raise ValueError(f"Invalid egg_type: {egg_type}")

    await process_calculate_set_time(entity)
    await process_set_status(entity)
    await process_clean_entity(entity)

    entity["requested_at"] = datetime.utcnow().isoformat()

    entity["status"] = entity["status"].lower()

    return entity