# ```python
import json
import logging
import os
import asyncio
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from common.config.config import ENTITY_VERSION
from common.app_init import entity_service
from common.service.trino_service import get_trino_schema_id_by_entity_name
from common.service.connections import ingest_data as ingest_data_func

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def generate_inventory_report_process(meta, data):
    """Process to generate inventory report from the SwaggerHub API."""
    try:
        logger.info("Starting inventory report generation process.")

        # Step 1: Ingest raw inventory data using the existing ingest_data function
        logger.info("Ingesting raw inventory data.")
        ingest_data_result = await ingest_data_func(meta, data)

        # Step 2: Process ingestion result and prepare inventory report data
        inventory_report_data = {
            "inventory_report_id": f"report_{data['job_id']}",
            "generated_at": data["scheduled_time"],
            "total_items": ingest_data_result.get("total_items"),
            "average_price": ingest_data_result.get("average_price"),
            "total_inventory_value": ingest_data_result.get("total_value"),
            "item_details": ingest_data_result.get("items", []),
            "report_summary": {
                "comments": "This report summarizes the inventory metrics.",
                "report_status": "Completed",
                "generated_by": "Inventory Management System"
            }
        }

        # Step 3: Save the inventory report entity
        inventory_report_entity_id = await entity_service.add_item(
            meta["token"],
            "inventory_report_entity",
            ENTITY_VERSION,
            inventory_report_data
        )
        logger.info(f"Inventory report entity saved with ID: {inventory_report_entity_id}")

    except Exception as e:
        logger.error(f"Error in generate_inventory_report_process: {e}")
        raise

# Test cases
class TestGenerateInventoryReportProcess(IsolatedAsyncioTestCase):

    @patch("common.app_init.entity_service.add_item")
    @patch("common.service.connections.ingest_data")
    def test_generate_inventory_report_process(self, mock_ingest_data, mock_entity_service):
        # Arrange: Set up mock return values
        mock_ingest_data.return_value = {
            "total_items": 150,
            "average_price": 25.5,
            "total_value": 3825.0,
            "items": [
                {
                    "item_id": "item_001",
                    "item_name": "Widget A",
                    "quantity": 30,
                    "unit_price": 20.0,
                    "total_value": 600.0
                },
                {
                    "item_id": "item_002",
                    "item_name": "Widget B",
                    "quantity": 50,
                    "unit_price": 25.0,
                    "total_value": 1250.0
                }
            ]
        }
        mock_entity_service.return_value = "inventory_report_entity_id"

        meta = {"token": "test_token"}
        data = {
            "job_id": "12345",
            "scheduled_time": "2023-10-02T08:00:00Z"
        }

        # Act: Call the process function
        asyncio.run(generate_inventory_report_process(meta, data))

        # Assert: Check that the appropriate methods were called with expected arguments
        mock_ingest_data.assert_called_once_with(meta, data)
        mock_entity_service.assert_called_once_with(
            meta["token"],
            "inventory_report_entity",
            ENTITY_VERSION,
            {
                "inventory_report_id": "report_12345",
                "generated_at": "2023-10-02T08:00:00Z",
                "total_items": 150,
                "average_price": 25.5,
                "total_inventory_value": 3825.0,
                "item_details": [
                    {
                        "item_id": "item_001",
                        "item_name": "Widget A",
                        "quantity": 30,
                        "unit_price": 20.0,
                        "total_value": 600.0
                    },
                    {
                        "item_id": "item_002",
                        "item_name": "Widget B",
                        "quantity": 50,
                        "unit_price": 25.0,
                        "total_value": 1250.0
                    }
                ],
                "report_summary": {
                    "comments": "This report summarizes the inventory metrics.",
                    "report_status": "Completed",
                    "generated_by": "Inventory Management System"
                }
            }
        )

if __name__ == "__main__":
    import unittest
    unittest.main()
# ``` 
# 
# This code snippet implements the `generate_inventory_report_process` function, which utilizes the existing `ingest_data` function to retrieve inventory data and generates an inventory report. It also includes a test class that mocks the necessary services and tests the process to ensure it behaves as expected.