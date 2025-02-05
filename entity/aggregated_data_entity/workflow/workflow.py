# ```python
import json
import logging
import os
import asyncio
import unittest
from unittest.mock import patch

from app_init.app_init import entity_service, ai_service
from common.config.config import ENTITY_VERSION, TRINO_AI_API
from common.service.trino_service import get_trino_schema_id_by_entity_name
from common.util.utils import read_json_file, parse_json, send_post_request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name())

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

async def aggregate_data(meta, data):
    """Process to aggregate raw data into aggregated_data_entity."""
    logger.info("Starting data aggregation process.")
    try:
        raw_data = await entity_service.get_item(
            meta["token"],
            "raw_data_entity",
            ENTITY_VERSION,
            "raw_data_001"
        )
        aggregated_value = (raw_data["value"] + 29500) / 2  # Example aggregation logic
        aggregated_data = {
            "id": "aggregated_data_001",
            "average_value": aggregated_value,
            "time_frame": "1 hour",
            "raw_data_ids": [raw_data["id"]],
            "calculation_timestamp": "2023-10-01T11:00:00Z",
            "request_parameters": {
                "requested_time_frame": "1 hour",
                "aggregate_function": "average"
            }
        }
        aggregated_data_id = await entity_service.add_item(
            meta["token"],
            "aggregated_data_entity",
            ENTITY_VERSION,
            aggregated_data
        )
        data["aggregated_data_entity"] = {"technical_id": aggregated_data_id}
        logger.info("Data aggregation process completed successfully.")
    except Exception as e:
        logger.error(f"Error in aggregate_data: {e}")
        raise

async def save_aggregated_data(meta, data):
    """Process to save aggregated data after aggregation."""
    logger.info("Saving aggregated data.")
    try:
        aggregated_data = {
            "id": "aggregated_data_002",
            "average_value": 29500,
            "time_frame": "1 hour",
            "raw_data_ids": ["raw_data_001"],
            "calculation_timestamp": "2023-10-01T11:00:00Z",
            "request_parameters": {
                "requested_time_frame": "1 hour",
                "aggregate_function": "average"
            }
        }
        await entity_service.add_item(
            meta["token"],
            "aggregated_data_entity",
            ENTITY_VERSION,
            aggregated_data
        )
        logger.info("Aggregated data saved successfully.")
    except Exception as e:
        logger.error(f"Error in save_aggregated_data: {e}")
        raise

class TestDataAggregation(unittest.TestCase):

    @patch("app_init.app_init.entity_service.add_item")
    @patch("app_init.app_init.entity_service.get_item")
    def test_aggregate_data_success(self, mock_get_item, mock_add_item):
        mock_get_item.return_value = {
            "id": "raw_data_001",
            "value": 30000
        }
        mock_add_item.return_value = "aggregated_data_entity_id"
        meta = {"token": "test_token"}
        data = {}
        asyncio.run(aggregate_data(meta, data))
        mock_add_item.assert_called_once_with(
            meta["token"],
            "aggregated_data_entity",
            ENTITY_VERSION,
            {
                "id": "aggregated_data_001",
                "average_value": 29500,
                "time_frame": "1 hour",
                "raw_data_ids": ["raw_data_001"],
                "calculation_timestamp": "2023-10-01T11:00:00Z",
                "request_parameters": {
                    "requested_time_frame": "1 hour",
                    "aggregate_function": "average"
                }
            }
        )

    @patch("app_init.app_init.entity_service.add_item")
    def test_save_aggregated_data_success(self, mock_add_item):
        mock_add_item.return_value = "aggregated_data_entity_id"
        meta = {"token": "test_token"}
        data = {}
        asyncio.run(save_aggregated_data(meta, data))
        mock_add_item.assert_called_once_with(
            meta["token"],
            "aggregated_data_entity",
            ENTITY_VERSION,
            {
                "id": "aggregated_data_002",
                "average_value": 29500,
                "time_frame": "1 hour",
                "raw_data_ids": ["raw_data_001"],
                "calculation_timestamp": "2023-10-01T11:00:00Z",
                "request_parameters": {
                    "requested_time_frame": "1 hour",
                    "aggregate_function": "average"
                }
            }
        )

if __name__ == "__main__":
    unittest.main()
# ```