import logging
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def process_set_initial_status(entity: dict):
    entity["status"] = "processing"
    entity["requestedAt"] = datetime.utcnow().isoformat() + "Z"

async def process_fetch_weather_data(entity: dict):
    OPENWEATHER_API_KEY = "YOUR_OPENWEATHER_API_KEY"  # TODO: insert valid API key here
    OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
    city = entity.get("city")
    if not city:
        raise ValueError("Missing 'city' attribute in entity")

    async with httpx.AsyncClient() as client:
        params = {"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"}
        try:
            response = await client.get(OPENWEATHER_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            entity["weather_data"] = data
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error when fetching weather data for city '{city}': {e.response.status_code}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error when fetching weather data for city '{city}': {e}")
            raise

async def process_calculate_results(entity: dict):
    weather_data = entity.get("weather_data")
    if not weather_data:
        raise ValueError("Missing weather_data in entity")

    temp_celsius = weather_data.get("main", {}).get("temp")
    if temp_celsius is None:
        raise ValueError("Temperature data missing in API response")

    temp_fahrenheit = temp_celsius * 9 / 5 + 32

    weather_desc_list = weather_data.get("weather", [])
    weather_description = None
    if weather_desc_list and isinstance(weather_desc_list, list):
        weather_description = weather_desc_list[0].get("description")

    result = {
        "city": entity.get("city"),
        "temperature_celsius": temp_celsius,
        "temperature_fahrenheit": temp_fahrenheit,
        "weather_description": weather_description,
        "processedAt": datetime.utcnow().isoformat() + "Z",
    }
    entity["result"] = result

async def process_set_final_status(entity: dict, success: bool = True, error_message: str = None):
    now_iso = datetime.utcnow().isoformat() + "Z"
    if success:
        entity["status"] = "completed"
    else:
        entity["status"] = "failed"
        entity["result"] = {"error": error_message}
    entity["completedAt"] = now_iso