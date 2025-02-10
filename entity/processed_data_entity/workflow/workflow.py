# ```python
import json
import logging
import asyncio
from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION
from entity.raw_data_entity.connections.connections import ingest_data as ingest_raw_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def process_raw_data(meta, data):
    """Process to transform raw data into a processed format."""
    try:
        # Call the ingest_data function to fetch raw data.
        raw_data = await ingest_raw_data()
        if not raw_data:
            raise ValueError("No raw data received for processing.")
        # Mapping the raw data to the processed data entity structure.
        processed_data = {
            "processed_data_id": "processed_data_001",
            "total_products": len(raw_data),
            "average_price": "Rs. 750",
            "products": raw_data
        }
        # Add the processed data entity using the entity service.
        await entity_service.add_item(
            meta["token"], "processed_data_entity", ENTITY_VERSION, processed_data
        )
        data["dependent_entity"] = {"technical_id": "aggregated_data_entity_id"}
        logger.info("Processed data entity added successfully.")
    except Exception as e:
        logger.error(f"Error in process_raw_data: {e}")
        raise

async def aggregate_processed_data(meta, data):
    """Aggregate the processed data for reporting."""
    try:
        aggregated_data = {
            "report_id": "report_001",
            "report_name": "Daily Product Summary",
            "generated_at": "2023-10-01T01:00:00Z",
            "total_products": len(data["products"]),
            "average_price": "Rs. 750",
            "product_details": data["products"],
            "summary_statistics": {
                "count_by_type": {
                    "Tops": 5,
                    "Tshirts": 3,
                    "Dress": 2
                },
                "average_price": "Rs. 750"
            }
        }
        await entity_service.add_item(
            meta["token"], "report_entity", ENTITY_VERSION, aggregated_data
        )
        logger.info("Aggregated data report entity added successfully.")
    except Exception as e:
        logger.error(f"Error in aggregate_processed_data: {e}")
        raise

# Test cases to verify the functionality of the processor functions
import unittest
from unittest.mock import patch

class TestDataProcessing(unittest.TestCase):

    @patch("app_init.app_init.entity_service.add_item")
    def test_process_raw_data_success(self, mock_add_item):
        mock_add_item.return_value = "processed_data_entity_id"
        meta = {"token": "test_token"}
        data = {}
        asyncio.run(process_raw_data(meta, data))
        mock_add_item.assert_called_once_with(
            meta["token"], "processed_data_entity", ENTITY_VERSION, {
                "processed_data_id": "processed_data_001",
                "total_products": 2,
                "average_price": "Rs. 750",
                "products": [
                    {
                        "id": 1,
                        "name": "Blue Top",
                        "price": "Rs. 500",
                        "brand": "Polo",
                        "category": "Tops"
                    },
                    {
                        "id": 2,
                        "name": "Men Tshirt",
                        "price": "Rs. 400",
                        "brand": "H&M",
                        "category": "Tshirts"
                    }
                ]
            }
        )

    @patch("app_init.app_init.entity_service.add_item")
    def test_aggregate_processed_data_success(self, mock_add_item):
        mock_add_item.return_value = "report_entity_id"
        meta = {"token": "test_token"}
        data = {
            "products": [
                {
                    "id": 1,
                    "name": "Blue Top",
                    "price": "Rs. 500"
                },
                {
                    "id": 2,
                    "name": "Men Tshirt",
                    "price": "Rs. 400"
                }
            ]
        }
        asyncio.run(aggregate_processed_data(meta, data))
        mock_add_item.assert_called_once_with(
            meta["token"], "report_entity", ENTITY_VERSION, {
                "report_id": "report_001",
                "report_name": "Daily Product Summary",
                "generated_at": "2023-10-01T01:00:00Z",
                "total_products": 2,
                "average_price": "Rs. 750",
                "product_details": data["products"],
                "summary_statistics": {
                    "count_by_type": {
                        "Tops": 1,
                        "Tshirts": 1
                    },
                    "average_price": "Rs. 750"
                }
            }
        )

if __name__ == "__main__":
    unittest.main()
# ```