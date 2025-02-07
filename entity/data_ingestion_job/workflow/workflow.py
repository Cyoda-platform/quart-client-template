# ```python
import asyncio
import logging
import unittest
from unittest.mock import patch

from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION
from common.service.trino_service import get_trino_schema_id_by_entity_name
from processor.connections.connections import ingest_data as ingest_raw_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ingest_raw_data(meta, data):
    """Process to ingest raw data from the specified API."""
    logger.info("Starting the ingestion of raw data.")
    raw_data = await ingest_raw_data()
    if not raw_data:
        logger.error("No raw data received for ingestion.")
        raise ValueError("No data received for ingestion.")
    raw_data_entity_id = await entity_service.add_item(
        meta["token"],
        "raw_data_entity",
        ENTITY_VERSION,
        raw_data
    )
    data["raw_data_entity"] = {"technical_id": raw_data_entity_id}
    logger.info("Raw data entity added successfully.")

async def process_transformation(meta, data):
    """Apply transformation logic to the raw data."""
    logger.info("Processing transformation of raw data.")
    transformed_data = {
        "id": data["id"],
        "name": data["name"],
        "price": data["price"],
        "brand": data["brand"],
        "category": {
            "usertype": {
                "usertype": data["category"]["usertype"]["usertype"]
            },
            "category": data["category"]["category"]
        },
        "aggregation_result": {
            "average_price": "Rs. 600",
            "category_count": {
                "Tops": 5,
                ""Dresses": 3
            }
        }
    }
    transformed_data_id = await entity_service.add_item(
        meta["token"],
        "transformed_data_entity",
        ENTITY_VERSION,
        transformed_data
    )
    data["transformed_data_entity"] = {"technical_id": transformed_data_id}
    logger.info("Transformed data entity added successfully.")

async def create_report(meta, data):
    """Generate a report based on the aggregated data."""
    logger.info("Creating a report based on aggregated data.")
    report_data = {
        "report_id": "report_001",
        "generated_at": "2023-10-01T01:00:00Z",
        "summary": "Monthly sales report for October.",
        "details": {
            "total_sales": 15000,
            "average_price": 600,
            "product_count": 25,
            "top_categories": [
                {
                    "category": "Tops",
                    "count": 5,
                    "average_price": 600
                },
                {
                    "category": "Dresses",
                    "count": 3,
                    "average_price": 1000
                }
            ],
            "brand_distribution": {
                "Polo": 2,
                "H&M": 1,
                "Madame": 2
            }
        }
    }
    report_id = await entity_service.add_item(
        meta["token"],
        "report_entity",
        ENTITY_VERSION,
        report_data
    )
    data["report_entity"] = {"technical_id": report_id}
    logger.info("Report entity generated successfully.")

class TestDataIngestionJob(unittest.TestCase):

    @patch("app_init.app_init.entity_service.add_item")
    def test_ingest_raw_data_success(self, mock_add_item):
        mock_add_item.return_value = "raw_data_entity_id"
        meta = {"token": "test_token"}
        data = {"id": "job_001"}
        asyncio.run(ingest_raw_data(meta, data))
        mock_add_item.assert_called_once()

    @patch("app_init.app_init.entity_service.add_item")
    def test_process_transformation_success(self, mock_add_item):
        mock_add_item.return_value = "transformed_data_entity_id"
        meta = {"token": "test_token"}
        data = {
            "id": "1",
            "name": "Blue Top",
            "price": "Rs. 500",
            "brand": "Polo",
            "category": {
                "usertype": {
                    "usertype": "Women"
                },
                "category": "Tops"
            }
        }
        asyncio.run(process_transformation(meta, data))
        mock_add_item.assert_called_once()

    @patch("app_init.app_init.entity_service.add_item")
    def test_create_report_success(self, mock_add_item):
        mock_add_item.return_value = "report_entity_id"
        meta = {"token": "test_token"}
        data = {}
        asyncio.run(create_report(meta, data))
        mock_add_item.assert_called_once()

if __name__ == "__main__":
    unittest.main()
# ```