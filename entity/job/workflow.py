import logging
import unittest
from unittest.mock import patch, AsyncMock

from app_init.app_init import entity_service, cyoda_token
import aiohttp
import asyncio

from quart import jsonify

from common.config.config import ENTITY_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_report(data, meta={"token": "cyoda_token"}):
    """Initiates the report creation process and sends an email."""
    try:
        logger.info("create_report processor")
        email = data.get('email')  # Extract email from request data

        # Fetch Bitcoin conversion rates
        rates = await _fetch_bitcoin_rates()

        # Send email with the rates asynchronously


        # Save the report in memory
        data = {
            "btc_usd_rate": rates["btc_usd"],
            "btc_eur_rate": rates["btc_eur"],
            "timestamp": "2023-10-01T12:00:00Z"  # Placeholder for current timestamp
        }
        report_id = await entity_service.add_item(
            cyoda_token, 'report', ENTITY_VERSION, data
        )

        asyncio.create_task(_send_email(report_id, rates, email))

        return jsonify({"report_id": report_id, "status": "Report is being generated."}), 202

    except Exception as e:
        logger.error(f"Error in create_report: {e}")
        raise


async def _fetch_bitcoin_rates():
    """Fetch Bitcoin rates from CoinGecko."""
    async with aiohttp.ClientSession() as session:
        async with session.get(
                'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd,eur') as response:
            rates = await response.json()
            return {
                "btc_usd": rates['bitcoin']['usd'],
                "btc_eur": rates['bitcoin']['eur']
            }


async def _send_email(report_id, rates, recipient_email):
    """Send an email with the Bitcoin conversion rates."""
    sender_email = "your_email@example.com"  # TODO: Replace with your email
    sender_password = "your_password"  # TODO: Replace with your email password

    logger.info("Sending email")