# Certainly! Here’s the implementation of the processor functions for `data_ingestion_job`, including `ingest_raw_data`, `aggregate_data`, and `create_report`. I'll ensure to reuse the existing functions from the codebase, particularly the `ingest_data` function. I'll also include unit tests in the same file to validate the functionality.
# 
# ### Implementation of Processor Functions
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

async def aggregate_data(meta, data):
    logger.info("Starting data aggregation process.")
    try:
        # Extract raw data from the ingestion data
        activities = data["raw_data_entity"]["records"]

        # Simulate aggregation logic
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
        logger.error(f"Error in aggregate_data: {e}")
        raise

async def create_report(meta, data):
    logger.info("Starting report creation process.")
    try:
        report_data = {
            "report_id": "report_001",
            "generated_at": "2023-10-01T10:00:00Z",
            "report_title": "Monthly Data Analysis",
            "summary": data["aggregated_data_entity"]["summary"],  # Using the aggregated data
            "distribution_info": {},
        }

        # Save the report entity
        report_entity_id = await entity_service.add_item(
            meta["token"], "report_entity", ENTITY_VERSION, report_data
        )

        # Log the report generation
        logger.info(f"Report entity saved successfully with ID: {report_entity_id}")
    except Exception as e:
        logger.error(f"Error in create_report: {e}")
        raise

# Unit Tests
import unittest
from unittest.mock import patch

class TestDataIngestionJob(unittest.TestCase):

    @patch("entity.raw_data_entity.connections.connections.ingest_data")
    @patch("app_init.app_init.entity_service.add_item")
    def test_ingest_raw_data(self, mock_add_item, mock_ingest_data):
        mock_ingest_data.return_value = [{"id": 1, "firstName": "John", "lastName": "Doe", "completed": False}]
        mock_add_item.return_value = "raw_data_entity_id"

        meta = {"token": "test_token"}
        data = {}

        asyncio.run(ingest_raw_data(meta, data))

        mock_add_item.assert_called_once_with(
            meta["token"], "raw_data_entity", ENTITY_VERSION,
            [{"id": 1, "firstName": "John", "lastName": "Doe", "completed": False}]
        )

    @patch("app_init.app_init.entity_service.add_item")
    def test_aggregate_data(self, mock_add_item):
        mock_add_item.return_value = "aggregated_data_entity_id"

        meta = {"token": "test_token"}
        data = {
            "raw_data_entity": {
                "technical_id": "raw_data_entity_001",
                "records": [
                    {"id": 1, "firstName": "John", "lastName": "Doe", "completed": False},
                    {"id": 2, "firstName": "Jane", "lastName": "Doe", "completed": True}
                ]
            }
        }

        asyncio.run(aggregate_data(meta, data))

        # Ensure the data counts are correct:
        total_activities = len(data["raw_data_entity"]["records"])
        completed_activities = sum(1 for record in data["raw_data_entity"]["records"] if record["completed"])
        pending_activities = total_activities - completed_activities

        mock_add_item.assert_called_once_with(
            meta["token"], "aggregated_data_entity", ENTITY_VERSION,
            {
                "total_activities": total_activities,
                "completed_activities": completed_activities,
                "pending_activities": pending_activities,
                "activity_summary": data["raw_data_entity"]["records"],
            }
        )

    @patch("app_init.app_init.entity_service.add_item")
    def test_create_report(self, mock_add_item):
        mock_add_item.return_value = "report_entity_id"

        meta = {"token": "test_token"}
        data = {
            "aggregated_data_entity": {
                "summary": {
                    "total_activities": 2,
                    "completed_activities": 1,
                    "pending_activities": 1
                }
            }
        }

        asyncio.run(create_report(meta, data))

        mock_add_item.assert_called_once_with(
            meta["token"], "report_entity", ENTITY_VERSION,
            {
                "report_id": "report_001",
                "generated_at": "2023-10-01T10:00:00Z",
                "report_title": "Monthly Data Analysis",
                "summary": data["aggregated_data_entity"]["summary"],
                "distribution_info": {}
            }
        )

if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Summary of the Implementation:
# - **Processor Functions**: The code includes three main asynchronous processor functions:
#   - `ingest_raw_data`: Fetches and saves raw data.
#   - `aggregate_data`: Processes the raw data and generates aggregated insights.
#   - `create_report`: Generates a report based on the aggregated data.
# 
# - **Unit Tests**: I included unit tests for each processor function using `unittest` and `unittest.mock` to simulate external service calls, ensuring that the functions work correctly without needing to interact with real services.
# 
# Each test checks if the appropriate entity service methods are called with the expected parameters, validating the logic of the processor functions.
# 
# If you have any questions or need further clarifications on any part of this implementation, just let me know! 😊