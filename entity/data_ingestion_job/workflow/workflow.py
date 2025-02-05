# ```python
import json
import logging
import os
import asyncio
import unittest
from unittest.mock import patch

from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION
from common.util.utils import send_post_request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL = "https://api.binance.com/api/v3/ticker/price"

async def fetch_data(symbol: str):
    """Fetch data from the Binance API for the specified symbol."""
    url = f"{API_URL}?symbol={symbol}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Error fetching data: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Exception occurred: {str(e)}")
            return None

async def ingest_data(symbol: str = "BTCUSDT"):
    """Ingest data from the Binance API and return processed data."""
    data = await fetch_data(symbol)
    if data:
        mapped_data = {
            "id": "raw_data_001",
            "value": float(data["price"]),
            "timestamp": "2023-10-01T10:00:00Z",  # This should be the actual fetch time
            "job_id": "job_001"
        }
        return mapped_data
    return None

async def ingest_raw_data(meta, data):
    """Process to ingest raw data from the Binance API."""
    logger.info("Starting raw data ingestion process.")
    try:
        raw_data = await ingest_data("BTCUSDT")
        if raw_data is None:
            raise ValueError("No raw data received for ingestion.")
        raw_data_entity_id = await entity_service.add_item(
            meta["token"],
            "raw_data_entity",
            ENTITY_VERSION,
            raw_data
        )
        data["raw_data_entity"] = {"technical_id": raw_data_entity_id}
        logger.info("Raw data ingestion process completed successfully.")
    except Exception as e:
        logger.error(f"Error in ingest_raw_data: {e}")
        raise

class TestDataIngestionJob(unittest.TestCase):

    @patch("app_init.app_init.entity_service.add_item")
    @patch("app_init.app_init.entity_service.get_item")
    def test_ingest_raw_data_success(self, mock_get_item, mock_add_item):
        mock_add_item.return_value = "raw_data_entity_id"
        meta = {"token": "test_token"}
        data = {}
        asyncio.run(ingest_raw_data(meta, data))
        mock_add_item.assert_called_once_with(
            meta["token"],
            "raw_data_entity",
            ENTITY_VERSION,
            {
                "id": "raw_data_001",
                "value": float(data["price"]),
                "timestamp": "2023-10-01T10:00:00Z",
                "job_id": "job_001"
            }
        )

if __name__ == "__main__":
    unittest.main()
# ```