# Here’s the implementation for the processor functions related to the `crocodile_data_ingestion_job`. This includes the functions `fetch_crocodile_data`, `store_crocodile_data`, and `complete_ingestion`, following your requirements to reuse existing functions and ensure proper handling of entities.
# 
# ```python
import json
import logging
import asyncio
from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION
from common.service.trino_service import run_sql_query
from common.util.utils import send_post_request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fetch_crocodile_data(meta, data):
    """Fetch crocodile data from the API."""
    logger.info("Fetching crocodile data from API.")
    try:
        # API request to fetch crocodiles data
        response = await send_post_request(meta["token"], data["api_url"])
        if response.status_code == 200:
            crocodiles = response.json()
            data["crocodiles"] = crocodiles
            logger.info("Crocodile data fetched successfully.")
        else:
            logger.error(f"Failed to fetch data: {response.content}")
            raise Exception("Error fetching crocodile data.")
    except Exception as e:
        logger.error(f"Error in fetch_crocodile_data: {e}")
        raise

async def store_crocodile_data(meta, data):
    """Store the fetched crocodile data into the database."""
    logger.info("Storing crocodile data.")
    try:
        for croc in data["crocodiles"]:
            # Adding each crocodile entity using entity_service
            crocodile_entity_id = await entity_service.add_item(
                meta["token"], "crocodile_entity", ENTITY_VERSION, croc
            )
            logger.info(f"Crocodile entity saved with ID: {crocodile_entity_id}")
    except Exception as e:
        logger.error(f"Error in store_crocodile_data: {e}")
        raise

async def complete_ingestion(meta, data):
    """Finalize the data ingestion process."""
    logger.info("Completing the data ingestion process.")
    try:
        # Update the job status or perform any finalization logic
        data["status"] = "complete"
        logger.info("Data ingestion completed successfully.")
    except Exception as e:
        logger.error(f"Error in complete_ingestion: {e}")
        raise


# Unit Tests
import unittest
from unittest.mock import patch

class TestCrocodileDataIngestionJob(unittest.TestCase):

    @patch("common.util.utils.send_post_request")
    @patch("app_init.app_init.entity_service.add_item")
    async def test_fetch_crocodile_data(self, mock_add_item, mock_send_post_request):
        mock_send_post_request.return_value.status_code = 200
        mock_send_post_request.return_value.json.return_value = [
            {"id": "croc_001", "name": "Chompers", "sex": "Male", "age": 5},
            {"id": "croc_002", "name": "Sally", "sex": "Female", "age": 4},
        ]

        meta = {"token": "test_token"}
        data = {"api_url": "https://test-api.k6.io/public/crocodiles/"}

        await fetch_crocodile_data(meta, data)

        self.assertIn("crocodiles", data)
        self.assertEqual(len(data["crocodiles"]), 2)

    @patch("app_init.app_init.entity_service.add_item")
    def test_store_crocodile_data(self, mock_add_item):
        mock_add_item.side_effect = ["crocodile_entity_id_1", "crocodile_entity_id_2"]

        meta = {"token": "test_token"}
        data = {
            "crocodiles": [
                {"id": "croc_001", "name": "Chompers", "sex": "Male", "age": 5},
                {"id": "croc_002", "name": "Sally", "sex": "Female", "age": 4},
            ]
        }

        asyncio.run(store_crocodile_data(meta, data))

        self.assertEqual(mock_add_item.call_count, 2)

    def test_complete_ingestion(self):
        meta = {"token": "test_token"}
        data = {"status": "pending"}

        asyncio.run(complete_ingestion(meta, data))

        self.assertEqual(data["status"], "complete")


if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Explanation of the Code:
# 1. **Processor Functions**:
#    - **`fetch_crocodile_data`**: This function fetches crocodile data from the specified API and saves it into the `data` dictionary. It logs success and error messages accordingly.
#    - **`store_crocodile_data`**: It iterates over the retrieved crocodile data and saves each record using the `entity_service.add_item()` method. It logs each saved entity's ID.
#    - **`complete_ingestion`**: This function finalizes the ingestion process, updating the job status to "complete".
# 
# 2. **Unit Tests**:
#    - The test class `TestCrocodileDataIngestionJob` uses `unittest` to create tests for each processor function.
#    - Mocks are used to simulate external calls and verify that functions work correctly in isolation, enabling you to run tests without hitting actual services.
# 
# Let me know if you need any more adjustments or explanations! 😊