import logging
import asyncio
from app_init.app_init import entity_service
from entity.user_data_entity.connections.connections import ingest_data as ingest_user_data
from common.config.config import ENTITY_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fetch_user_data(meta, data):
    """Fetch user data from the API and save it as raw data."""
    logger.info("Fetching user data from the API.")
    raw_user_data = await ingest_user_data()  # Removed token parameter
    
    if not raw_user_data:
        logger.error("No user data fetched.")
        raise ValueError("No user data available.")

    # Save the raw user data entity
    user_data_entity_id = await entity_service.add_item(
        meta["token"], "user_data_entity", ENTITY_VERSION, raw_user_data
    )
    logger.info(f"Raw user data saved successfully with ID: {user_data_entity_id}")

    data["user_data_entity"] = {"technical_id": user_data_entity_id, "records": raw_user_data}

async def process_user_data(meta, data):
    """Transform the fetched user data into a structured format."""
    logger.info("Processing user data.")
    user_records = data["user_data_entity"]["records"]
    
    # Example transformation logic
    transformed_data = [
        {
            "id": user["id"],
            "user_id": user["id"],  # Reference to the original user
            "transformed_name": user["userName"],
            "transformed_email": f"{user['userName'].lower()}@example.com",  # Example email transformation
            "status": "Active",  # Assume all fetched users are active for simplicity
            "transformation_timestamp": "2023-10-01T10:00:00Z"  # Example timestamp
        } for user in user_records
    ]

    # Save the transformed user data entity
    transformed_user_data_entity_id = await entity_service.add_item(
        meta["token"], "transformed_user_data_entity", ENTITY_VERSION, transformed_data
    )
    logger.info(f"Transformed user data saved successfully with ID: {transformed_user_data_entity_id}")

    data["transformed_user_data_entity"] = {"technical_id": transformed_user_data_entity_id, "records": transformed_data}

async def save_data(meta, data):
    """Save the transformed user data to the database."""
    logger.info("Saving transformed user data.")
    # This function may already be handled in process_user_data, but can include additional save logic if needed.

async def create_report(meta, data):
    """Generate a monthly report based on the transformed user data."""
    logger.info("Generating monthly report.")
    total_users = len(data["transformed_user_data_entity"]["records"])
    active_users = sum(1 for user in data["transformed_user_data_entity"]["records"] if user["status"] == "Active")
    inactive_users = total_users - active_users

    report_data = {
        "report_id": "report_2023_10",
        "month": "2023-10",
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "generated_at": "2023-10-01T10:05:00Z",
        "comments": "Monthly report for October 2023."
    }

    # Save the monthly report entity
    monthly_report_entity_id = await entity_service.add_item(
        meta["token"], "monthly_report_entity", ENTITY_VERSION, report_data
    )
    logger.info(f"Monthly report saved successfully with ID: {monthly_report_entity_id}")

    data["monthly_report_entity"] = {"technical_id": monthly_report_entity_id}

async def email_report(meta, data):
    """Send the generated report to the admin's email."""
    logger.info("Sending monthly report to admin.")
    # Assume some logic here to send the report via email
    # For demonstration, simply log the action
    logger.info("Email sent to admin with report ID: {}".format(data["monthly_report_entity"]["technical_id"]))

# Unit Tests
import unittest
from unittest.mock import patch, AsyncMock

class TestBatchProcessingOrchestration(unittest.TestCase):

    @patch("app_init.app_init.entity_service.add_item")
    @patch("entity.user_data_entity.connections.connections.ingest_data")
    async def test_fetch_user_data(self, mock_ingest_data, mock_add_item):
        mock_ingest_data.return_value = [{"id": 1, "userName": "User 1", "password": "Password1"}]
        mock_add_item.return_value = "user_data_entity_id"

        meta = {"token": "test_token"}
        data = {}

        await fetch_user_data(meta, data)

        mock_add_item.assert_called_once_with(
            meta["token"], "user_data_entity", ENTITY_VERSION, mock_ingest_data.return_value
        )
        self.assertIn("user_data_entity", data)

    @patch("app_init.app_init.entity_service.add_item")
    def test_process_user_data(self, mock_add_item):
        mock_add_item.return_value = "transformed_user_data_entity_id"

        meta = {"token": "test_token"}
        data = {
            "user_data_entity": {
                "records": [{"id": 1, "userName": "User 1"}]
            }
        }

        asyncio.run(process_user_data(meta, data))

        mock_add_item.assert_called_once()
        self.assertIn("transformed_user_data_entity", data)

    @patch("app_init.app_init.entity_service.add_item")
    def test_create_report(self, mock_add_item):
        mock_add_item.return_value = "monthly_report_entity_id"

        meta = {"token": "test_token"}
        data = {
            "transformed_user_data_entity": {
                "records": [{"id": 1, "transformed_name": "User 1", "status": "Active"}]
            }
        }

        asyncio.run(create_report(meta, data))

        mock_add_item.assert_called_once()
        self.assertIn("monthly_report_entity", data)

    @patch("app_init.app_init.entity_service.add_item")
    def test_email_report(self, mock_add_item):
        meta = {}
        data = {
            "monthly_report_entity": {
                "technical_id": "monthly_report_entity_id"
            }
        }

        asyncio.run(email_report(meta, data))

if __name__ == "__main__":
    unittest.main()