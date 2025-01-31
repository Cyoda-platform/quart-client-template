# ```python
from quart import Quart, request, jsonify
import asyncio
import logging
from app_init.app_init import entity_service
from entity.data_ingestion_job.connections.connections import ingest_crocodiles_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Quart(__name__)

@app.route('/api/data_ingestion_job', methods=['POST'])
async def create_data_ingestion_job():
    """API endpoint to save the data ingestion job entity."""
    try:
        # Extract data from the request
        request_data = await request.get_json()
        token = request_data.get("token")
        
        if not token:
            return jsonify({"error": "Authentication token is required."}), 400
        
        # Call the data ingestion function
        await ingest_crocodiles_data({"token": token}, request_data)

        # Optionally, you can return a success message or the created entity ID
        return jsonify({"message": "Data ingestion job created successfully."}), 201

    except Exception as e:
        logger.error(f"Error creating data ingestion job: {e}")
        return jsonify({"error": str(e)}), 500

# Unit tests
import unittest
from unittest.mock import patch

class TestDataIngestionJobAPI(unittest.TestCase):

    @patch("app_init.app_init.entity_service.add_item")
    @patch("entity.data_ingestion_job.connections.connections.ingest_crocodiles_data")
    def test_create_data_ingestion_job_success(self, mock_ingest_data, mock_add_item):
        # Arrange: Set up mock return values
        mock_ingest_data.return_value = None  # Assume it ingests data successfully
        mock_add_item.return_value = "data_ingestion_job_id"

        app.testing = True
        with app.test_client() as client:
            # Act: Make a POST request to the API endpoint
            response = client.post('/api/data_ingestion_job', json={"token": "test_token"})

            # Assert: Check the response
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json, {"message": "Data ingestion job created successfully."})
            mock_ingest_data.assert_called_once()

    @patch("entity.data_ingestion_job.connections.connections.ingest_crocodiles_data")
    def test_create_data_ingestion_job_missing_token(self, mock_ingest_data):
        app.testing = True
        with app.test_client() as client:
            # Act: Make a POST request without a token
            response = client.post('/api/data_ingestion_job', json={})

            # Assert: Check the response for error
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json, {"error": "Authentication token is required."})

    @patch("entity.data_ingestion_job.connections.connections.ingest_crocodiles_data")
    def test_create_data_ingestion_job_failure(self, mock_ingest_data):
        # Simulating an error during ingestion
        mock_ingest_data.side_effect = Exception("Failed to ingest data.")

        app.testing = True
        with app.test_client() as client:
            response = client.post('/api/data_ingestion_job', json={"token": "test_token"})

            self.assertEqual(response.status_code, 500)
            self.assertEqual(response.json, {"error": "Failed to ingest data."})

if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Explanation of the Code:
# 1. **Quart API Endpoint**:
#    - The `/api/data_ingestion_job` endpoint accepts POST requests to create a new data ingestion job.
#    - It extracts the token and calls the `ingest_crocodiles_data` function.
#    - Returns a success message upon successful ingestion, or error messages for failures.
# 
# 2. **Unit Tests**:
#    - The test class `TestDataIngestionJobAPI` contains tests to verify the functionality of the API endpoint.
#    - **`test_create_data_ingestion_job_success`**: Tests the successful creation of a data ingestion job.
#    - **`test_create_data_ingestion_job_missing_token`**: Tests the response when the token is missing.
#    - **`test_create_data_ingestion_job_failure`**: Tests the response when there’s an error during the ingestion process.
# 
# This setup allows users to test the API functionality in an isolated environment using mocks for external service calls.