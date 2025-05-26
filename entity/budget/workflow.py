import httpx
import asyncio
import logging

logger = logging.getLogger(__name__)

AI_MODEL_API = "https://api.mockforecast.ai/forecast"  # TODO: replace with real AI forecasting API

def now_iso():
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"

async def process_forecast(entity: dict):
    try:
        results = {}
        forecast_options = entity.get("forecastOptions", {})
        budget_data = entity.get("budgetData", {})

        if forecast_options.get("useAIModel"):
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(AI_MODEL_API, json={"budget": budget_data})
                if resp.status_code == 200:
                    results = resp.json().get("forecastResults", {})
                else:
                    logger.warning(f"AI model responded with status {resp.status_code}")
        else:
            results = {dep: {"forecasted": val, "variance": 0} for dep, val in budget_data.items()}

        entity["status"] = "completed"
        entity["results"] = results
        logger.info(f"Forecast completed: {entity.get('technicalId') or entity.get('forecastId')}")
    except Exception as e:
        entity["status"] = "error"
        logger.exception(e)

async def process_budget(entity: dict):
    entity.setdefault("status", "queued")
    entity.setdefault("requestedAt", now_iso())

    forecast_id = entity.get("technicalId") or entity.get("forecastId")
    if not forecast_id:
        return entity

    # Orchestrate workflow: trigger forecast processing task
    asyncio.create_task(process_forecast(entity))

    return entity