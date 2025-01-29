# ```python
import asyncio
import logging
from app_init.app_init import entity_service
from entity.user_data_entity.connections.connections import ingest_data as ingest_user_data
import unittest
from unittest.mock import patch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_user_details(meta, data):
    """Process to send GET request to ReqRes API and retrieve user information."""
    user_id = data["user_id"]
    logger.info(f"Retrieving details for user ID: {user_id}")

    # Check if the user ID is provided
    if user_id is None:
        logger.error("User ID is not provided.")
        raise ValueError("User ID is required.")

    # Fetch user data from ReqRes API using an external connection
    raw_data = await ingest_user_data(user_id)
    
    if raw_data is None:
        logger.error("No data received for ingestion.")
        return {}

    # Save the resulting user data to the corresponding raw data entity
    user_data_entity = {
        "id": raw_data["data"]["id"],
        "email": raw_data["data"]["email"],
        "first_name": raw_data["data"]["first_name"],
        "last_name": raw_data["data"]["last_name"],
        "avatar": raw_data["data"]["avatar"]
    }
    
    # Add the user data to the repository
    user_data_entity_id = await entity_service.add_item(
        meta["token"], "user_data_entity", "v1", user_data_entity
    )

    logger.info(f"User data entity saved successfully with ID: {user_data_entity_id}")
    return user_data_entity

# Unit Tests
class TestGetUserDetails(unittest.TestCase):

    @patch("app_init.app_init.entity_service.add_item")
    @patch("workflow.ingest_user_data")
    def test_get_user_details_success(self, mock_ingest_data, mock_add_item):
        # Arrange: set up mock return values
        mock_ingest_data.return_value = {
            "data": {
                "id": 2,
                "email": "janet.weaver@reqres.in",
                "first_name": "Janet",
                "last_name": "Weaver",
                "avatar": "https://reqres.in/img/faces/2-image.jpg"
            }
        }
        mock_add_item.return_value = "user_data_entity_id"

        meta = {"token": "test_token"}
        data = {"user_id": 2}

        # Act: run the function
        result = asyncio.run(get_user_details(meta, data))

        # Assert: verify that expected functions were called
        mock_ingest_data.assert_called_once_with(2)
        mock_add_item.assert_called_once_with(
            meta["token"], "user_data_entity", "v1", {
                "id": 2,
                "email": "janet.weaver@reqres.in",
                "first_name": "Janet",
                "last_name": "Weaver",
                "avatar": "https://reqres.in/img/faces/2-image.jpg"
            }
        )
        self.assertEqual(result["id"], 2)
        self.assertEqual(result["email"], "janet.weaver@reqres.in")

    @patch("workflow.ingest_user_data")
    def test_get_user_details_no_user_id(self, mock_ingest_data):
        # Arrange
        meta = {"token": "test_token"}
        data = {"user_id": None}  # No user ID provided

        # Act and Assert
        with self.assertRaises(ValueError):
            asyncio.run(get_user_details(meta, data))

if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Explanation of the Code
# 
# 1. **`get_user_details(meta, data)` Function**:
#    - This function retrieves user details based on the user ID provided in the `data` argument.
#    - It calls the `ingest_data` function to fetch user data from the ReqRes API.
#    - After retrieval, it maps the data to the expected structure and saves it using the `entity_service`.
# 
# 2. **Unit Tests**:
#    - The `TestGetUserDetails` class contains tests for successful retrieval of user details and handling of errors when no user ID is provided.
#    - The tests mock external service calls to ensure that the functionality is tested in isolation without making actual API calls.
# 
# This structure allows for efficient reuse of existing code and thorough testing of the functionality, ensuring that it meets user requirements.