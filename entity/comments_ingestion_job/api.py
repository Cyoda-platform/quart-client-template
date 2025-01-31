# Here’s a `api.py` file for a Quart application that allows you to save the entity `comments_ingestion_job`. The file includes the endpoint to trigger the comments ingestion job and tests with mocks for external services or functions.
# 
# ```python
from quart import Quart, request, jsonify
import asyncio
import logging

app = Quart(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage for demo purposes
comments_ingestion_jobs = []

# Function to save the comments_ingestion_job entity
async def save_comments_ingestion_job(data):
    comments_ingestion_jobs.append(data)
    return data["job_id"]

@app.route('/api/comments_ingestion_job', methods=['POST'])
async def create_comments_ingestion_job():
    job_data = await request.get_json()
    
    logger.info("Received request to create comments ingestion job.")

    # Simulate processing logic here; in real implementation, you would call your processing function
    job_data["status"] = "pending"
    job_data["job_id"] = f"job_{len(comments_ingestion_jobs) + 1}"
    job_data["scheduled_time"] = job_data.get("scheduled_time", "now")
    
    # Save the job
    saved_job = await save_comments_ingestion_job(job_data)

    logger.info(f"Comments ingestion job created with ID: {saved_job}.")
    return jsonify(saved_job), 201

# Testing with Mocks
import unittest
from unittest.mock import patch

class TestCommentsIngestionAPI(unittest.TestCase):

    @patch("quart.request.get_json")
    def test_create_comments_ingestion_job(self, mock_get_json):
        mock_get_json.return_value = {
            "job_name": "Test Job",
            "post_id": 1,
            "scheduled_time": "2023-10-01T05:00:00Z"
        }

        with app.test_client() as client:
            response = client.post('/api/comments_ingestion_job')
            self.assertEqual(response.status_code, 201)

            # Check that the job was saved correctly
            self.assertEqual(len(comments_ingestion_jobs), 1)
            self.assertEqual(comments_ingestion_jobs[0]["job_name"], "Test Job")
            self.assertEqual(comments_ingestion_jobs[0]["post_id"], 1)

if __name__ == '__main__':
    app.run()
    unittest.main()
# ```
# 
# ### Explanation of the Code:
# 1. **Quart API Endpoint**:
#    - **POST /api/comments_ingestion_job**: This endpoint receives a JSON request to create a new comments ingestion job. It builds the job data, sets a pending status, generates a unique job ID, and saves it to an in-memory list for demonstration purposes.
# 
# 2. **Testing with Mocks**:
#    - The tests use `unittest` and `unittest.mock` to create a mock request to the API, simulating the ingestion job creation process without actual external calls.
#    - The test checks for the correct status code and validates that the job was saved with the expected attributes.
# 
# This setup allows you to quickly test the API functionality in an isolated environment. If you have any further requests or need adjustments, just let me know!