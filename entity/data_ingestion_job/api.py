# ```python
import logging
from quart import Quart, request, jsonify
from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Quart(__name__)

@app.route("/api/v1/data_ingestion_job", methods=["POST"])
async def create_data_ingestion_job():
    """API endpoint to create a new data ingestion job."""
    try:
        data = await request.json
        token = request.headers.get("Authorization")  # Assuming token is passed in the header

        # Save the data_ingestion_job entity
        job_id = await entity_service.add_item(
            token, "data_ingestion_job", ENTITY_VERSION, data
        )

        return jsonify({"status": "success", "job_id": job_id}), 201
    except Exception as e:
        logger.error(f"Error creating data ingestion job: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Testing with Mocks
import unittest
from unittest.mock import patch

class TestDataIngestionJobAPI(unittest.TestCase):

    @patch("app_init.app_init.entity_service.add_item")
    def test_create_data_ingestion_job_success(self, mock_add_item):
        mock_add_item.return_value = "job_id_001"

        app.testing = True
        with app.test_client() as client:
            response = client.post(
                "/api/v1/data_ingestion_job",
                json={
                    "job_id": "job_2023_10_01",
                    "scheduled_time": "2023-10-01T10:00:00Z",
                    "status": "completed",
                    "description": "Daily job to ingest data from the SwaggerHub API for inventory activities.",
                    "request_parameters": {
                        "accept": "text/plain; v=1.0"
                    },
                    "ingested_data_summary": {
                        "total_items_ingested": 2,
                        "items": [
                            {
                                "id": 1,
                                "title": "Activity 1",
                                "dueDate": "2025-01-22T21:36:27.6587562+00:00",
                                "completed": False
                            },
                            {
                                "id": 2,
                                "title": "Activity 2",
                                "dueDate": "2025-01-22T22:36:27.6587592+00:00",
                                "completed": True
                            }
                        ]
                    },
                    "reporting": {
                        "generated_at": "2023-10-01T10:05:00Z",
                        "summary": "This report summarizes the data ingested from the SwaggerHub API during the scheduled job."
                    }
                },
                headers={"Authorization": "test_token"}
            )

            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json, {"status": "success", "job_id": "job_id_001"})

if __name__ == "__main__":
    unittest.main()
# ```