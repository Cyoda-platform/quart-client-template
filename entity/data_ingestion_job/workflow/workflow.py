# ```python
import asyncio
import logging
from app_init.app_init import entity_service
from entity.raw_crocodile_entity.connections.connections import ingest_data as ingest_raw_data
from common.config.config import ENTITY_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ingest_crocodiles_data(meta, data):
    """Process to ingest crocodile data from the specified API."""
    try:
        # Call the ingest_data function to fetch crocodile data
        raw_data = await ingest_raw_data(meta["token"])

        if raw_data is None or len(raw_data) == 0:
            logger.warning("No data retrieved during ingestion.")
            return

        # Save the raw data entity
        raw_crocodile_entity_id = await entity_service.add_item(
            meta["token"], "raw_crocodile_entity", ENTITY_VERSION, raw_data
        )

        # Update the data with the raw crocodile entity ID
        data["raw_crocodile_entity"] = {
            "technical_id": raw_crocodile_entity_id,
            "records": raw_data
        }
        logger.info(f"Raw crocodile entity saved successfully with ID: {raw_crocodile_entity_id}")

    except Exception as e:
        logger.error(f"Error in ingest_crocodiles_data: {e}")
        raise

# Unit tests
import unittest
from unittest.mock import patch

class TestDataIngestionJob(unittest.TestCase):

    @patch("app_init.app_init.entity_service.add_item")
    @patch("entity.raw_crocodile_entity.connections.connections.ingest_data")
    async def test_ingest_crocodiles_data(self, mock_ingest_data, mock_add_item):
        # Mocking the data that would be returned by ingest_data
        mock_ingest_data.return_value = [
            {"id": 1, "name": "Bert", "sex": "M", "date_of_birth": "2010-06-27", "age": 14},
            {"id": 2, "name": "Ed", "sex": "M", "date_of_birth": "1995-02-27", "age": 29}
        ]
        mock_add_item.return_value = "raw_crocodile_entity_id"

        meta = {"token": "test_token"}
        data = {}

        await ingest_crocodiles_data(meta, data)

        # Assertions to ensure the mock functions were called correctly
        mock_ingest_data.assert_called_once_with(meta["token"])
        mock_add_item.assert_called_once_with(meta["token"], "raw_crocodile_entity", ENTITY_VERSION, mock_ingest_data.return_value)
        self.assertIn("raw_crocodile_entity", data)
        self.assertEqual(data["raw_crocodile_entity"]["technical_id"], "raw_crocodile_entity_id")
        self.assertEqual(len(data["raw_crocodile_entity"]["records"]), 2)  # Checking if we have two records

if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Explanation of the Code:
# 1. **`ingest_crocodiles_data()` Function**:
#    - This async function is responsible for ingesting crocodile data. It calls the `ingest_data` function to fetch data from the specified API.
#    - Upon successful data retrieval, it saves the raw data as `raw_crocodile_entity` and updates the `data` argument with the technical ID and records.
# 
# 2. **Unit Tests**:
#    - The test class `TestDataIngestionJob` contains a single test method `test_ingest_crocodiles_data`.
#    - Mocks for the `add_item` function from `entity_service` and `ingest_data` function are used to simulate the external service calls.
#    - Assertions ensure that the functions were called with the right parameters, and the data has been successfully updated with the new entity information.
# 
# This implementation allows users to quickly test the data ingestion process in an isolated environment without relying on actual external service calls.