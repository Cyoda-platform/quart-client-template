# Here’s the implementation of the processor function `ingest_raw_data` for the `data_ingestion_job`. This function will be responsible for calling the existing `ingest_data` function to retrieve raw data from the SwaggerHub API and saving it to the corresponding `raw_data_entity`. Additionally, I will include tests to ensure the functionality works correctly in isolation.
# 
# ### Processor Functions Implementation
# 
# ```python
import logging
import asyncio
from app_init.app_init import entity_service
from entity.raw_data_entity.connections.connections import ingest_data as ingest_raw_data_connection
from common.config.config import ENTITY_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ingest_raw_data(meta, data):
    logger.info("Starting data ingestion process.")
    try:
        # Call the reusable ingest_data function
        raw_data = await ingest_raw_data_connection()

        # Save the raw data entity
        raw_data_entity_id = await entity_service.add_item(
            meta["token"], "raw_data_entity", ENTITY_VERSION, raw_data
        )

        # Update the data with the raw data entity ID
        data["raw_data_entity"] = {"technical_id": raw_data_entity_id, "records": raw_data}
        logger.info(f"Raw data entity saved successfully with ID: {raw_data_entity_id}")
    except Exception as e:
        logger.error(f"Error in ingest_raw_data: {e}")
        raise

# Testing with Mocks
import unittest
from unittest.mock import patch

class TestDataIngestionJob(unittest.TestCase):

    @patch("entity.raw_data_entity.connections.connections.ingest_data")
    @patch("app_init.app_init.entity_service.add_item")
    def test_ingest_raw_data(self, mock_add_item, mock_ingest_data):
        mock_ingest_data.return_value = [
            {"id": 1, "title": "Activity 1", "dueDate": "2025-01-22T21:36:27.6587562+00:00", "completed": False},
            {"id": 2, "title": "Activity 2", "dueDate": "2025-01-22T22:36:27.6587592+00:00", "completed": True}
        ]
        mock_add_item.return_value = "raw_data_entity_id"

        meta = {"token": "test_token"}
        data = {}

        asyncio.run(ingest_raw_data(meta, data))

        mock_add_item.assert_called_once_with(
            meta["token"], "raw_data_entity", ENTITY_VERSION, 
            [{"id": 1, "title": "Activity 1", "dueDate": "2025-01-22T21:36:27.6587562+00:00", "completed": False},
             {"id": 2, "title": "Activity 2", "dueDate": "2025-01-22T22:36:27.6587592+00:00", "completed": True}]
        )

if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Explanation of the Code
# 
# 1. **`ingest_raw_data` Function**: 
#    - This asynchronous function is responsible for orchestrating the data ingestion process.
#    - It calls the `ingest_data` function to retrieve raw data from the API.
#    - After receiving the data, it saves the `raw_data_entity` using the entity service and updates the `data` object with the technical ID of the saved entity.
# 
# 2. **Unit Tests**:
#    - The test class `TestDataIngestionJob` includes a test method `test_ingest_raw_data` that verifies the functionality of the `ingest_raw_data` function.
#    - It uses mocking to simulate the behavior of the `ingest_data` function and the entity service's `add_item` method.
#    - The test checks that the raw data is correctly ingested and that the corresponding raw data entity is saved in the repository.
# 
# ### Conclusion
# 
# This implementation ensures that the `ingest_raw_data` function works as intended, retrieving data from the external API and saving it to the appropriate entity. The tests provide confidence that the functionality can be executed successfully in an isolated environment. If you have any further questions or need additional modifications, please let me know!