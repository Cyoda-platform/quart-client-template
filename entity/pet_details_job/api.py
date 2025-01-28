# ```python
from quart import Quart, request, jsonify
import asyncio
from app_init.app_init import entity_service
from entity.pet_details_job.ingest_pet_process import ingest_pet_process  # Import the ingest function

app = Quart(__name__)

@app.route('/api/pet_details_job', methods=['POST'])
async def save_pet_details_job():
    """
    API endpoint to save pet details job.
    """
    data = await request.json
    token = request.headers.get("Authorization")  # Assuming token is passed in header

    try:
        # Call the ingest_pet_process function to process and save the pet details
        await ingest_pet_process({"token": token}, data)

        return jsonify({"message": "Pet details job processed successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Testing with Mocks
import unittest
from unittest.mock import patch

class TestPetDetailsJobAPI(unittest.TestCase):

    @patch("entity.pet_details_job.ingest_pet_process.ingest_pet_process")
    @patch("app_init.app_init.entity_service.add_item")
    def test_save_pet_details_job(self, mock_add_item, mock_ingest_pet_process):
        # Mock the ingest_pet_process to simulate processing
        mock_ingest_pet_process.return_value = None  # Simulating successful processing

        app.testing = True
        with app.test_client() as client:
            response = client.post('/api/pet_details_job', json={
                "job_name": "Daily Pet Details Ingestion Job",
                "scheduled_time": "2023-10-01T05:00:00Z"
            }, headers={"Authorization": "test_token"})

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json, {"message": "Pet details job processed successfully."})

    @patch("entity.pet_details_job.ingest_pet_process.ingest_pet_process")
    def test_save_pet_details_job_failure(self, mock_ingest_pet_process):
        # Simulate an error during processing
        mock_ingest_pet_process.side_effect = Exception("Processing error")

        app.testing = True
        with app.test_client() as client:
            response = client.post('/api/pet_details_job', json={
                "job_name": "Daily Pet Details Ingestion Job",
                "scheduled_time": "2023-10-01T05:00:00Z"
            }, headers={"Authorization": "test_token"})

            self.assertEqual(response.status_code, 500)
            self.assertEqual(response.json, {"error": "Processing error"})

if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Explanation:
# 1. **API Route**:
#    - The `/api/pet_details_job` endpoint processes incoming POST requests to save the `pet_details_job`.
#    - It extracts the token from the request headers and invokes the `ingest_pet_process` function to handle the ingestion logic based on the provided job data.
# 
# 2. **Testing**:
#    - Unit tests are provided using `unittest` and `unittest.mock` to mock the `ingest_pet_process` function.
#    - The tests verify both successful processing and handling of exceptions, simulating the expected behavior of the API in an isolated environment. 
# 
# This setup allows users to test the API functionality without dependencies on actual services, ensuring the integrity of the implementation.