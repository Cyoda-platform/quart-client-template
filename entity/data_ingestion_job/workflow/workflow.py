# Here's the implementation of the processor functions for the `data_ingestion_job`, including `ingest_raw_data`, `aggregate_raw_data_process`, and `generate_report_process`. I'll reuse the existing `ingest_data` function from `raw_data_entity/connections/connections.py`, and I'll ensure that the outputs are saved to their corresponding entities. 
# 
# The final code also includes tests with mocks for external services and functions to allow for isolated testing.
# 
# ```python
import logging
import asyncio
from app_init.app_init import entity_service
from entity.raw_data_entity.connections.connections import ingest_data as ingest_raw_data_connection
from common.config.config import ENTITY_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ingest_raw_data(meta, data):
    logger.info("Starting data ingestion process.")
    try:
        # Call the reusable ingest_data function
        raw_data = await ingest_raw_data_connection(meta["token"])

        # Save the raw data entity
        raw_data_entity_id = await entity_service.add_item(
            meta["token"], "raw_data_entity", ENTITY_VERSION, raw_data
        )
        
        # Update the data with the raw data entity ID
        data["raw_data_entity"] = {"technical_id": raw_data_entity_id, "records": raw_data}
        logger.info(f"Raw data entity saved successfully with ID: {raw_data_entity_id}")
    except Exception as e:
        logger.error(f"Error in ingest_raw_data: {e}")
        raise

async def aggregate_raw_data_process(meta, data):
    logger.info("Starting data aggregation process.")
    try:
        activities = data["raw_data_entity"]["records"]
        aggregated_data = {
            "total_activities": len(activities),
            "completed_activities": sum(1 for activity in activities if activity.get("completed")),
            "pending_activities": sum(1 for activity in activities if not activity.get("completed")),
            "activity_summary": activities,
        }

        # Save the aggregated data entity
        aggregated_data_entity_id = await entity_service.add_item(
            meta["token"], "aggregated_data_entity", ENTITY_VERSION, aggregated_data
        )
        
        # Update the data with the aggregated data entity ID
        data["aggregated_data_entity"] = {"technical_id": aggregated_data_entity_id}
        logger.info(f"Aggregated data entity saved successfully with ID: {aggregated_data_entity_id}")
    except Exception as e:
        logger.error(f"Error in aggregate_raw_data_process: {e}")
        raise

async def generate_report_process(meta, data):
    logger.info("Starting report generation process.")
    try:
        report_data = {
            "report_id": "report_001",
            "generated_at": "2023-10-01T10:00:00Z",
            "report_title": "Daily Data Processing Report",
            "summary": {
                "total_entries": data["aggregated_data_entity"]["total_activities"],
                "successful_ingests": data["aggregated_data_entity"]["completed_activities"],
                "failed_ingests": data["aggregated_data_entity"]["pending_activities"],
            },
            "distribution_info": {},
        }

        # Save the report entity
        report_entity_id = await entity_service.add_item(
            meta["token"], "report_entity", ENTITY_VERSION, report_data
        )
        
        # Log the report generation
        logger.info(f"Report entity saved successfully with ID: {report_entity_id}")
    except Exception as e:
        logger.error(f"Error in generate_report_process: {e}")
        raise

# Unit Tests
import unittest
from unittest.mock import patch

class TestDataIngestionJob(unittest.TestCase):

    @patch("app_init.app_init.entity_service.add_item")
    @patch("entity.raw_data_entity.connections.connections.ingest_data")
    def test_ingest_raw_data(self, mock_ingest_data, mock_add_item):
        mock_ingest_data.return_value = [{"id": 1, "idBook": 1, "firstName": "First Name 1", "lastName": "Last Name 1"}]
        mock_add_item.return_value = "raw_data_entity_id"

        meta = {"token": "test_token"}
        data = {}

        asyncio.run(ingest_raw_data(meta, data))

        mock_add_item.assert_called_once_with(
            meta["token"], "raw_data_entity", ENTITY_VERSION, mock_ingest_data.return_value
        )
        self.assertIn("raw_data_entity", data)
        self.assertEqual(data["raw_data_entity"]["technical_id"], "raw_data_entity_id")

    @patch("app_init.app_init.entity_service.add_item")
    def test_aggregate_raw_data_process(self, mock_add_item):
        mock_add_item.return_value = "aggregated_data_entity_id"

        meta = {"token": "test_token"}
        data = {
            "raw_data_entity": {
                "technical_id": "raw_data_entity_001",
                "records": [
                    {"id": 1, "idBook": 1, "firstName": "First Name 1", "lastName": "Last Name 1", "completed": True},
                    {"id": 2, "idBook": 1, "firstName": "First Name 2", "lastName": "Last Name 2", "completed": False},
                ]
            }
        }

        asyncio.run(aggregate_raw_data_process(meta, data))

        expected_aggregated_data = {
            "total_activities": 2,
            "completed_activities": 1,
            "pending_activities": 1,
            "activity_summary": data["raw_data_entity"]["records"],
        }

        mock_add_item.assert_called_once_with(
            meta["token"], "aggregated_data_entity", ENTITY_VERSION, expected_aggregated_data
        )
        self.assertIn("aggregated_data_entity", data)
        self.assertEqual(data["aggregated_data_entity"]["technical_id"], "aggregated_data_entity_id")

    @patch("app_init.app_init.entity_service.add_item")
    def test_generate_report_process(self, mock_add_item):
        mock_add_item.return_value = "report_entity_id"

        meta = {"token": "test_token"}
        data = {
            "aggregated_data_entity": {
                "technical_id": "aggregated_data_entity_001",
                "total_activities": 2,
                "completed_activities": 1,
                "pending_activities": 1,
            }
        }

        asyncio.run(generate_report_process(meta, data))

        expected_report_data = {
            "report_id": "report_001",
            "generated_at": "2023-10-01T10:00:00Z",
            "report_title": "Daily Data Processing Report",
            "summary": {
                "total_entries": 2,
                "successful_ingests": 1,
                "failed_ingests": 1,
            },
            "distribution_info": {},
        }

        mock_add_item.assert_called_once_with(
            meta["token"], "report_entity", ENTITY_VERSION, expected_report_data
        )

if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Explanation of the Code:
# 
# 1. **Processor Functions**:
#    - **ingest_raw_data**: This function calls the `ingest_data` function to fetch raw data and save it to the `raw_data_entity`.
#    - **aggregate_raw_data_process**: This function aggregates the ingested raw data and saves the result to the `aggregated_data_entity`.
#    - **generate_report_process**: This function generates a report based on aggregated data and saves it to the `report_entity`.
# 
# 2. **Unit Tests**: 
#    - The test class `TestDataIngestionJob` includes test methods for each processor function, using mocks for the `entity_service.add_item` and `ingest_data` functions to isolate tests.
#    - Assertions check that the correct functions are called and that the data is being updated appropriately.
# 
# This implementation ensures that you are reusing the existing functionality while creating new entities as needed. If you have any questions or require further modifications, feel free to ask!