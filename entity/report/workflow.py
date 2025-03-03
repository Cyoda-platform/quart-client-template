import asyncio
import logging
from datetime import datetime
import httpx

# Configure logger
logger = logging.getLogger(__name__)

# Process entity business logic functions (each accepts only 'entity' as argument)

async def process_mark_processing(entity: dict):
    # Mark entity as processing
    entity["status"] = "processing"

async def process_conversion_rates(entity: dict):
    # Fetch conversion rates and update entity with BTC prices
    url_btc_usd = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    url_btc_eur = "https://api.binance.com/api/v3/ticker/price?symbol=BTCEUR"
    try:
        async with httpx.AsyncClient() as client:
            resp_usd, resp_eur = await asyncio.gather(
                client.get(url_btc_usd),
                client.get(url_btc_eur)
            )
        data_usd = resp_usd.json()
        data_eur = resp_eur.json()
        entity["btc_usd"] = float(data_usd.get("price", 0))
        entity["btc_eur"] = float(data_eur.get("price", 0))
    except Exception as e:
        logger.exception("Error fetching conversion rates")
        raise

async def process_timestamp(entity: dict):
    # Set current timestamp on the entity
    entity["timestamp"] = datetime.utcnow().isoformat()

async def process_mark_completed(entity: dict):
    # Mark workflow as completed and applied
    entity["status"] = "completed"
    entity["workflow_applied"] = True

async def process_mark_failed(entity: dict):
    # Mark workflow as failed
    entity["status"] = "failed"

async def process_send_email(entity: dict):
    # Simulate async email sending
    await asyncio.sleep(0.1)
    logger.info(f"Email sent with report: {entity}")