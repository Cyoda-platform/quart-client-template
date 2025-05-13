import asyncio
import logging
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass

import httpx
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

async def process_fetch_external_api(entity: dict) -> None:
    # Business logic: fetch from external API and update entity data
    location = entity.get("location")
    parameters = entity.get("parameters", [])
    datetime_iso = entity.get("datetime")

    async with httpx.AsyncClient() as client:
        try:
            # TODO: Replace with MSC GeoMet API details
            WEATHERAPI_BASE_URL = "http://api.weatherapi.com/v1/current.json"
            WEATHERAPI_KEY = "demo"
            params = {
                "key": WEATHERAPI_KEY,
                "q": location,
                "aqi": "no"
            }
            response = await client.get(WEATHERAPI_BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            current = data.get("current", {})

            result = {}
            if "temperature" in parameters:
                result["temperature"] = current.get("temp_c")
            if "humidity" in parameters:
                result["humidity"] = current.get("humidity")
            if "wind_speed" in parameters:
                result["wind_speed"] = current.get("wind_kph")

            for param in parameters:
                if param not in result:
                    result[param] = None

            # Update entity data with fetched results
            entity["data"] = result
            entity["timestamp"] = datetime.utcnow().isoformat()
            entity["status"] = "fetched"
        except Exception as e:
            logger.error(f"Error fetching weather data: {e}")
            entity["status"] = "error"
            entity["error_message"] = str(e)

async def process_weather_fetch_result(entity: dict) -> dict:
    # Workflow orchestration only
    if entity.get("status") != "fetched":
        await process_fetch_external_api(entity)
    # Potentially other workflow steps here in future
    return entity