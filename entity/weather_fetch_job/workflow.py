import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def process_weather_fetch_job(entity: dict) -> dict:
    # Workflow orchestration only
    await process_validate_job(entity)
    await process_handle_locations(entity)
    await process_finish_job(entity)
    return entity

async def process_validate_job(entity: dict):
    job_id = entity.get("job_id")
    locations = entity.get("locations", [])
    if not job_id or not isinstance(locations, list) or not locations:
        entity["status"] = "failed"
        entity["error"] = "Invalid job_id or locations data"
        logger.error(f"process_validate_job: invalid input for job: {entity}")
        # Raise to stop workflow orchestration if invalid
        raise ValueError("Invalid job_id or locations data")
    entity["status"] = "processing"
    entity["started_at"] = datetime.utcnow().isoformat() + "Z"
    logger.info(f"Starting job {job_id} for {len(locations)} locations")

async def process_handle_locations(entity: dict):
    locations = entity.get("locations", [])
    for loc in locations:
        lat = loc.get("latitude")
        lon = loc.get("longitude")
        if lat is None or lon is None:
            logger.warning(f"Skipping location with missing coordinates: {loc}")
            continue

        # Simulate caching or processing by storing under a 'cache' key in entity
        # TODO: Replace with actual cache logic if needed
        cache_key = f"{lat}_{lon}"
        if "cache" not in entity:
            entity["cache"] = {}
        entity["cache"][cache_key] = {
            "latitude": lat,
            "longitude": lon,
            "processed_at": datetime.utcnow().isoformat() + "Z"
        }
        logger.info(f"Processed cache entity for ({lat},{lon})")

async def process_finish_job(entity: dict):
    entity["status"] = "done"
    entity["finished_at"] = datetime.utcnow().isoformat() + "Z"
    logger.info(f"Job {entity.get('job_id')} processing complete")