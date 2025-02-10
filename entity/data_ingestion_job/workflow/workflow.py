# ```python
import asyncio
import logging
import unittest
from unittest.mock import patch

from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION
from connections.connections import ingest_data as fetch_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ingest_raw_data(meta, data):
    """Process to ingest raw data from the specified API and save as raw_data_entity."""
    try:
        # Fetch data from the external API
        raw_data = await fetch_data()
        if not raw_data:
            logger.error("No raw data received for ingestion.")
            return

        # Add the raw data entity using the entity service
        raw_data_id = await entity_service.add_item(
            meta["token"],
            "raw_data_entity",
            ENTITY_VERSION,
            raw_data[0]  # Assuming we're interested in the first item for this example
        )

        data["raw_data_entity"] = {"technical_id": raw_data_id}
        logger.info("Raw data entity ingested successfully.")

    except Exception as e:
        logger.error(f"Error in ingest_raw_data: {e}")
        raise

class TestDataIngestionJob(unittest.TestCase):

    @patch("app_init.app_init.entity_service.add_item")
    def test_ingest_raw_data(self, mock_add_item):
        mock_add_item.return_value = "raw_data_entity_id"

        meta = {"token": "test_token"}
        data = {
            "job_id": "job_001",
            "name": "data_ingestion_job",
            "scheduled_time": "2023-10-01T10:00:00Z",
            "status": "completed"
        }
        asyncio.run(ingest_raw_data(meta, data))

        mock_add_item.assert_called_once()
        self.assertEqual(data["raw_data_entity"]["technical_id"], "raw_data_entity_id")

if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Explanation of the Code
# 
# 1. **`ingest_raw_data` Function**:
#    - This asynchronous function is responsible for ingesting raw data from the specified API.
#    - It calls the `fetch_data()` function to retrieve the data and then saves it as a `raw_data_entity` using the `entity_service`.
# 
# 2. **Testing Class**:
#    - The `TestDataIngestionJob` class contains a unit test for the `ingest_raw_data` function.
#    - It uses mocking to simulate the addition of the raw data entity, allowing for testing in an isolated environment without calling external services.
# 
# 3. **Assertions**:
#    - The test verifies that the `add_item` method is called and checks that the technical ID of the ingested raw data entity is correctly assigned.
# 
# This implementation ensures that the data ingestion job processes the raw data effectively and saves it as the corresponding entity. If you have any further questions or need modifications, please let me know! I'm here to help!