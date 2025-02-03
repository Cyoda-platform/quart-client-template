import json
import logging
import asyncio
from app_init.app_init import entity_service

# Mock ingest_data_connection for testing
async def ingest_data_connection(token):
    """Mock implementation of ingest_data_connection"""
    return {
        "id": 1,
        "name": "Test User",
        "username": "testuser",
        "email": "test@example.com",
        "phone": "123-456-7890",
        "website": "example.com",
        "company": {
            "name": "Test Company",
            "catchPhrase": "Test Phrase",
            "bs": "Test BS"
        }
    }

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ingest_user_data(meta, data):
    """Ingest user data from the specified API."""
    try:
        logger.info("Starting user data ingestion process.")
        raw_data = await ingest_data_connection(meta["token"])  # Reuse the ingest_data function
        if raw_data is None:
            logger.error("No raw data received.")
            return
        
        # Save raw data to user_entity
        user_entity_id = await entity_service.add_item(
            meta["token"], "user_entity", "1.0", raw_data
        )
        logger.info(f"User entity saved successfully with ID: {user_entity_id}")
        
        return user_entity_id  # Return ID for further processing
    except Exception as e:
        logger.error(f"Error in ingest_user_data: {e}")
        raise

async def save_user(meta, data):
    """Save the user data to the repository."""
    try:
        logger.info("Saving user data to the repository.")
        user_data = {
            "id": data["id"],
            "name": data["name"],
            "username": data["username"],
            "email": data["email"],
            "phone": data["phone"],
            "website": data["website"],
            "company": data["company"]
        }
        
        # Save user entity
        user_entity_id = await entity_service.add_item(
            meta["token"], "user_entity", "1.0", user_data
        )
        logger.info(f"User data saved with ID: {user_entity_id}")
        
        return user_entity_id
    except Exception as e:
        logger.error(f"Error in save_user: {e}")
        raise

async def create_related_entities(meta, data):
    """Create address and company entities based on user data."""
    try:
        logger.info("Creating related entities for user.")
        address_data = data.get("address")
        company_data = data.get("company")

        # Save address entity
        address_entity_id = await entity_service.add_item(
            meta["token"], "address_entity", "1.0", address_data
        )
        logger.info(f"Address entity saved with ID: {address_entity_id}")

        # Save company entity
        company_entity_id = await entity_service.add_item(
            meta["token"], "company_entity", "1.0", company_data
        )
        logger.info(f"Company entity saved with ID: {company_entity_id}")

        return {
            "address_entity_id": address_entity_id,
            "company_entity_id": company_entity_id
        }
    except Exception as e:
        logger.error(f"Error in create_related_entities: {e}")
        raise

# Test cases
import unittest
from unittest.mock import patch

class TestUserJobProcessors(unittest.TestCase):

    @patch("app_init.app_init.entity_service.add_item")
    def test_ingest_user_data(self, mock_add_item):
        mock_add_item.return_value = "user_entity_id"
        meta = {"token": "test_token"}
        data = {"id": 1}  # Minimal data to match function signature

        user_id = asyncio.run(ingest_user_data(meta, data))

        mock_add_item.assert_called_once()
        self.assertIsNotNone(user_id)

    @patch("app_init.app_init.entity_service.add_item")
    def test_save_user(self, mock_add_item):
        mock_add_item.return_value = "user_entity_id"
        meta = {"token": "test_token"}
        data = {
            "id": 1,
            "name": "Leanne Graham",
            "username": "Bret",
            "email": "Sincere@april.biz",
            "phone": "1-770-736-8031 x56442",
            "website": "hildegard.org",
            "company": {
                "name": "Romaguera-Crona",
                "catchPhrase": "Multi-layered client-server neural-net",
                "bs": "harness real-time e-markets"
            }
        }

        user_id = asyncio.run(save_user(meta, data))

        mock_add_item.assert_called_once()
        self.assertEqual(user_id, "user_entity_id")

    @patch("app_init.app_init.entity_service.add_item")
    def test_create_related_entities(self, mock_add_item):
        mock_add_item.side_effect = ["address_entity_id", "company_entity_id"]
        meta = {"token": "test_token"}
        data = {
            "address": {
                "street": "Kulas Light",
                "suite": "Apt. 556",
                "city": "Gwenborough",
                "zipcode": "92998-3874"
            },
            "company": {
                "name": "Romaguera-Crona",
                "catchPhrase": "Multi-layered client-server neural-net",
                "bs": "harness real-time e-markets"
            }
        }

        ids = asyncio.run(create_related_entities(meta, data))

        self.assertEqual(ids["address_entity_id"], "address_entity_id")
        self.assertEqual(ids["company_entity_id"], "company_entity_id")

if __name__ == "__main__":
    unittest.main()