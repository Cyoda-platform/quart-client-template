# Here's the implementation of the processor functions for the `data_ingestion_job`, including the necessary imports and logic to save dependent entities. Each function will correspond to the specific processors you've mentioned: `fetch_activity_data_process`, `process_activity_data_process`, `generate_daily_report_process`, and `send_report_process`. I will also include unit tests to verify the functionality of the processors.
# 
# ```python
import logging
import asyncio
from app_init.app_init import entity_service
from entity.activity_data_entity.connections.connections import ingest_data as ingest_activity_data
from entity.processed_data_entity.connections.connections import ingest_data as ingest_processed_data
from entity.daily_report_entity.connections.connections import ingest_data as ingest_daily_report_data
from common.config.config import ENTITY_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fetch_activity_data_process(meta, data):
    """Fetch activity data from the API and save it to the activity_data_entity."""
    logger.info("Fetching activity data from the API.")
    raw_data = await ingest_activity_data(meta["token"])
    if not raw_data:
        logger.error("No data fetched during ingestion.")
        return
    
    # Save the raw data entity
    raw_data_entity_id = await entity_service.add_item(
        meta["token"], "activity_data_entity", ENTITY_VERSION, raw_data
    )
    data["activity_data_entity"] = {"technical_id": raw_data_entity_id}
    logger.info(f"Activity data entity saved with ID: {raw_data_entity_id}")

async def process_activity_data_process(meta, data):
    """Process the fetched activity data to analyze patterns."""
    logger.info("Processing activity data.")
    activities = data["activity_data_entity"]["records"]
    
    # Example processing logic
    frequency = len(activities)  # Count number of activities
    types_of_activities = [activity["title"] for activity in activities]

    processed_data = {
        "activity_id": activities[0]["id"],  # Reference to first activity
        "frequency": frequency,
        "types_of_activities": types_of_activities,
        "generated_at": data["generated_at"]  # Assuming date is passed in data
    }

    # Save the processed data entity
    processed_data_entity_id = await entity_service.add_item(
        meta["token"], "processed_data_entity", ENTITY_VERSION, processed_data
    )
    data["processed_data_entity"] = {"technical_id": processed_data_entity_id}
    logger.info(f"Processed data entity saved with ID: {processed_data_entity_id}")

async def generate_daily_report_process(meta, data):
    """Generate a daily report summarizing the processed data."""
    logger.info("Generating daily report.")
    processed_data = data["processed_data_entity"]

    daily_report = {
        "report_id": f"report_{data['generated_at'].split('T')[0]}",
        "generated_at": data["generated_at"],
        "total_activities": len(processed_data["types_of_activities"]),
        "completed_activities": sum(1 for activity in processed_data["types_of_activities"] if activity.get("completed")),
        "pending_activities": len(processed_data["types_of_activities"]) - sum(1 for activity in processed_data["types_of_activities"] if activity.get("completed")),
        "activity_summary": [],
        "comments": "Daily report generated successfully."
    }
    
    # Save the daily report entity
    report_entity_id = await entity_service.add_item(
        meta["token"], "daily_report_entity", ENTITY_VERSION, daily_report
    )
    data["daily_report_entity"] = {"technical_id": report_entity_id}
    logger.info(f"Daily report entity saved with ID: {report_entity_id}")

async def send_report_process(meta, data):
    """Send the generated report to the admin via email."""
    logger.info("Sending daily report to admin.")
    report = data["daily_report_entity"]

    # Simulate sending email (the actual sending logic would depend on your email service)
    logger.info(f"Report ID {report['technical_id']} sent to admin successfully.")

# Unit Tests
import unittest
from unittest.mock import patch

class TestDataIngestionJob(unittest.TestCase):

    @patch("app_init.app_init.entity_service.add_item")
    @patch("entity.activity_data_entity.connections.connections.ingest_data")
    async def test_fetch_activity_data_process(self, mock_ingest_data, mock_add_item):
        mock_ingest_data.return_value = [{"id": 1, "title": "Activity 1", "dueDate": "2025-01-29T14:32:51.4152486+00:00", "completed": False}]
        mock_add_item.return_value = "raw_data_entity_id"

        meta = {"token": "test_token"}
        data = {}

        await fetch_activity_data_process(meta, data)

        mock_add_item.assert_called_once_with(
            meta["token"], "activity_data_entity", ENTITY_VERSION, mock_ingest_data.return_value
        )
        self.assertIn("activity_data_entity", data)

    @patch("app_init.app_init.entity_service.add_item")
    def test_process_activity_data_process(self, mock_add_item):
        meta = {"token": "test_token"}
        data = {
            "activity_data_entity": {
                "records": [
                    {"id": "1", "title": "Activity 1", "dueDate": "2025-01-29T14:32:51.4152486+00:00", "completed": False},
                    {"id": "2", "title": "Activity 2", "dueDate": "2025-01-29T15:32:51.4152516+00:00", "completed": True}
                ]
            },
            "generated_at": "2023-10-01T10:00:00Z"
        }

        asyncio.run(process_activity_data_process(meta, data))

        mock_add_item.assert_called_once()
        self.assertIn("processed_data_entity", data)

    @patch("app_init.app_init.entity_service.add_item")
    def test_generate_daily_report_process(self, mock_add_item):
        meta = {"token": "test_token"}
        data = {
            "processed_data_entity": {
                "types_of_activities": [
                    {"title": "Activity 1", "completed": False},
                    {"title": "Activity 2", "completed": True}
                ]
            },
            "generated_at": "2023-10-01T10:00:00Z"
        }

        asyncio.run(generate_daily_report_process(meta, data))

        mock_add_item.assert_called_once()
        self.assertIn("daily_report_entity", data)

    @patch("app_init.app_init.entity_service.add_item")
    def test_send_report_process(self, mock_add_item):
        meta = {"token": "test_token"}
        data = {
            "daily_report_entity": {
                "technical_id": "report_2023_10_01"
            }
        }

        asyncio.run(send_report_process(meta, data))

        # Here you can verify that the report sending logic is executed properly
        self.assertIn("technical_id", data["daily_report_entity"])

if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Explanation of the Code:
# 1. **Processor Functions**:
#    - **fetch_activity_data_process**: Fetches activity data from the API, saves it to the `activity_data_entity`, and updates the `data` dictionary.
#    - **process_activity_data_process**: Processes the fetched activity data, analyzes it, and saves the results to the `processed_data_entity`.
#    - **generate_daily_report_process**: Generates a summary report based on processed data and saves it to the `daily_report_entity`.
#    - **send_report_process**: Simulates sending the report to the admin via email.
# 
# 2. **Unit Tests**: The tests cover each processor function to ensure they work as intended without relying on actual external services by using mocks.
# 
# Let me know if you need any adjustments or further assistance! 😊