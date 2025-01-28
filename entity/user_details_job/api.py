# ```python
from quart import Quart, request, jsonify
import asyncio
import logging
from app_init.app_init import entity_service
from common.service.user_data_entity.connections.connections import ingest_data as ingest_user_data
from pydantic import BaseModel, ValidationError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Quart(__name__)

class UserDetailsJob(BaseModel):
    user_id: int

@app.route('/user_details_job', methods=['POST'])
async def create_user_details_job():
    try:
        # Validate and parse the request body
        body = await request.get_json()
        user_details_job = UserDetailsJob(**body)

        # Call the get_user_details function
        meta = {"token": "dummy_token"}  # Replace with actual token retrieval logic
        data = {"user_id": user_details_job.user_id}
        user_data = await get_user_details(meta, data)

        # Save the user data entity
        await entity_service.add_item(
            meta["token"], "user_data_entity", "v1", user_data
        )

        return jsonify({"status": "success", "data": user_data}), 201

    except ValidationError as ve:
        logger.error(f"Validation error: {ve.json()}")
        return jsonify({"status": "error", "errors": ve.errors()}), 400
    except Exception as e:
        logger.error(f"Error in creating user details job: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

async def get_user_details(meta, data):
    """Process to send GET request to ReqRes API and retrieve user information."""
    user_id = data["user_id"]
    logger.info(f"Retrieving details for user ID: {user_id}")

    # Fetch user data from ReqRes API using the ingest_user_data function
    raw_data = await ingest_user_data(user_id)
    
    if raw_data is None:
        logger.error("No data received for ingestion.")
        return {}

    return {
        "id": raw_data["data"]["id"],
        "email": raw_data["data"]["email"],
        "first_name": raw_data["data"]["first_name"],
        "last_name": raw_data["data"]["last_name"],
        "avatar": raw_data["data"]["avatar"]
    }

# Unit Tests
from quart import Quart
import unittest
from unittest.mock import patch

class TestUserDetailsJobAPI(unittest.TestCase):
    @patch('app_init.app_init.entity_service.add_item')
    @patch('common.service.user_data_entity.connections.connections.ingest_data')
    def test_create_user_details_job_success(self, mock_ingest_data, mock_add_item):
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

        app.testing = True
        client = app.test_client()
        
        # Act: make a POST request to create a user details job
        response = client.post('/user_details_job', json={"user_id": 2})

        # Assert: check that the response is as expected
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["status"], "success")
        self.assertEqual(response.json["data"]["id"], 2)
        self.assertEqual(response.json["data"]["email"], "janet.weaver@reqres.in")

    @patch('common.service.user_data_entity.connections.connections.ingest_data')
    def test_create_user_details_job_validation_error(self, mock_ingest_data):
        app.testing = True
        client = app.test_client()

        # Act: make a POST request with missing user_id
        response = client.post('/user_details_job', json={})

        # Assert: check that the validation error response is as expected
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["status"], "error")

if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Explanation of the Code
# 
# 1. **Quart API Setup**:
#    - The API is set up using Quart to handle incoming requests for creating user details jobs.
#    - A `UserDetailsJob` Pydantic model is used to validate the incoming JSON request containing the user ID.
# 
# 2. **POST `/user_details_job` Endpoint**:
#    - This endpoint receives a user ID, fetches user details from the ReqRes API using the `get_user_details` function, and saves the user data entity through `entity_service`.
# 
# 3. **`get_user_details` Function**:
#    - The function retrieves user details based on the user ID passed from the request.
# 
# 4. **Unit Tests**:
#    - The `TestUserDetailsJobAPI` class includes tests for the API endpoint, mocking external service calls to ensure that the functionality can be tested in isolation without making actual API requests.
#    - Tests cover successful creation of a user details job and the handling of validation errors when required data is missing.
# 
# This code can be executed in an isolated environment to test the functionality of the Quart API for creating user details jobs.