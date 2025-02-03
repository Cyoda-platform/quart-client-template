# Certainly! Below is an implementation of a `api.py` file for saving the `data_ingestion_job` entity using Quart. This implementation includes the necessary API endpoint to handle the saving of the entity, along with tests that use mocks to ensure the functionality can be tested in an isolated environment.
# 
# ### Implementation of `api.py`
# 
# ```python
from quart import Quart, request, jsonify
from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Quart(__name__)

@app.route('/data_ingestion_job', methods=['POST'])
async def save_data_ingestion_job():
    data = await request.json
    try:
        job_id = data.get("job_id")
        job_name = data.get("job_name")
        scheduled_time = data.get("scheduled_time")
        status = data.get("status")
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        total_records_processed = data.get("total_records_processed")
        successful_records = data.get("successful_records")
        failed_records = data.get("failed_records")
        failure_reason = data.get("failure_reason", [])
        
        # Building the entity for saving
        entity_data = {
            "job_id": job_id,
            "job_name": job_name,
            "scheduled_time": scheduled_time,
            "status": status,
            "start_time": start_time,
            "end_time": end_time,
            "total_records_processed": total_records_processed,
            "successful_records": successful_records,
            "failed_records": failed_records,
            "failure_reason": failure_reason
        }

        # Save the entity
        saved_entity_id = await entity_service.add_item(
            request.headers.get("token"), "data_ingestion_job", ENTITY_VERSION, entity_data
        )
        return jsonify({"message": "Data ingestion job saved successfully.", "entity_id": saved_entity_id}), 201

    except Exception as e:
        logger.error(f"Error saving data ingestion job: {e}")
        return jsonify({"error": str(e)}), 500

# Unit Tests
import unittest
from unittest.mock import patch

class TestDataIngestionJobAPI(unittest.TestCase):

    @patch("app_init.app_init.entity_service.add_item")
    def test_save_data_ingestion_job(self, mock_add_item):
        mock_add_item.return_value = "ingestion_job_id"
        app.testing = True
        client = app.test_client()

        # Sample data for the job
        job_data = {
            "job_id": "ingestion_job_001",
            "job_name": "Daily Author Data Ingestion",
            "scheduled_time": "2023-10-01T05:00:00Z",
            "status": "scheduled",
            "start_time": "2023-10-01T05:00:00Z",
            "end_time": "2023-10-01T05:05:00Z",
            "total_records_processed": 100,
            "successful_records": 95,
            "failed_records": 5,
            "failure_reason": ["Timeout while fetching data"]
        }

        response = client.post('/data_ingestion_job', json=job_data, headers={"token": "test_token"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["message"], "Data ingestion job saved successfully.")
        self.assertEqual(response.json["entity_id"], "ingestion_job_id")

    @patch("app_init.app_init.entity_service.add_item")
    def test_save_data_ingestion_job_error(self, mock_add_item):
        mock_add_item.side_effect = Exception("Database error")
        app.testing = True
        client = app.test_client()

        # Sample data for the job
        job_data = {
            "job_id": "ingestion_job_001",
            "job_name": "Daily Author Data Ingestion",
            "scheduled_time": "2023-10-01T05:00:00Z",
            "status": "scheduled",
            "start_time": "2023-10-01T05:00:00Z",
            "end_time": "2023-10-01T05:05:00Z",
            "total_records_processed": 100,
            "successful_records": 95,
            "failed_records": 5
        }

        response = client.post('/data_ingestion_job', json=job_data, headers={"token": "test_token"})
        self.assertEqual(response.status_code, 500)
        self.assertIn("Database error", response.json["error"])

if __name__ == "__main__":
    app.run(debug=True)
    unittest.main()
# ```
# 
# ### Summary of the Implementation:
# - **API Endpoint**: The `/data_ingestion_job` endpoint is defined to handle POST requests for saving the data ingestion job entity.
# - **Data Handling**: The incoming JSON data is parsed, and the relevant fields are extracted to build the entity structure.
# - **Error Handling**: If anything goes wrong while saving the entity, an error message is logged, and a 500 response is returned.
#   
# ### Unit Tests:
# - **`test_save_data_ingestion_job`**: This test mocks the `add_item` method of the entity service to simulate saving the ingestion job entity. It checks if the API returns a successful response with the expected message and entity ID.
# - **`test_save_data_ingestion_job_error`**: This test simulates a failure in saving the entity by raising an exception. It checks that the API returns a 500 error response with the appropriate error message.
# 
# These tests allow you to verify the functionality of the API in an isolated environment without needing to interact with real external services.
# 
# If you have any questions or need further clarifications on any aspect, feel free to ask! 😊