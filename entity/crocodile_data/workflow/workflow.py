import asyncio
import logging
from app_init.app_init import entity_service
from entity.crocodile_data.connections.connections import ingest_data as ingest_raw_data_connection
from common.config.config import ENTITY_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ingest_raw_data(meta, data):
    logger.info("Starting data ingestion process.")
    try:
        # Call the reusable ingest_data function
        raw_data = await ingest_raw_data_connection() # Removed token parameter since function takes no args
        
        # Save the crocodile_data entity
        crocodile_data_entity_id = await entity_service.add_item(
            meta["token"], "crocodile_data", ENTITY_VERSION, raw_data
        )
        
        # Update the data with the crocodile_data entity ID
        data["crocodile_data"] = {"technical_id": crocodile_data_entity_id, "records": raw_data}
        logger.info(f"Crocodile data saved successfully with ID: {crocodile_data_entity_id}")
    except Exception as e:
        logger.error(f"Error in ingest_raw_data: {e}")
        raise

async def store_data_in_db(meta, data):
    logger.info("Starting data storage process.")
    try:
        # Assuming data["crocodile_data"] contains the required entity mapping
        if "crocodile_data" in data:
            stored_entity_id = await entity_service.add_item(
                meta["token"], "crocodile_data", ENTITY_VERSION, data["crocodile_data"]
            )
            logger.info(f"Crocodile data stored successfully with ID: {stored_entity_id}")
        else:
            logger.error("Crocodile data not found in the provided data.")
    except Exception as e:
        logger.error(f"Error in store_data_in_db: {e}")
        raise

# Testing with Mocks
import unittest
from unittest.mock import patch, ANY

class TestCrocodileDataProcessor(unittest.TestCase):

    @patch("entity.crocodile_data.connections.connections.ingest_data")
    @patch("app_init.app_init.entity_service.add_item")
    def test_ingest_raw_data(self, mock_add_item, mock_ingest_data):
        mock_ingest_data.return_value = [
            {"id": 1, "name": "Bert", "sex": "M", "date_of_birth": "2010-06-27", "age": 14},
            {"id": 2, "name": "Ed", "sex": "M", "date_of_birth": "1995-02-27", "age": 29},
            {"id": 3, "name": "Lyle the Crocodile", "sex": "M", "date_of_birth": "1985-03-03", "age": 39},
            {"id": 4, "name": "Solomon", "sex": "M", "date_of_birth": "1993-12-25", "age": 31},
            {"id": 5, "name": "The gharial", "sex": "F", "date_of_birth": "2004-06-28", "age": 20},
            {"id": 6, "name": "Sang Buaya", "sex": "F", "date_of_birth": "2006-01-28", "age": 19},
            {"id": 7, "name": "Sobek", "sex": "F", "date_of_birth": "1854-09-02", "age": 170},
            {"id": 8, "name": "Curious George", "sex": "M", "date_of_birth": "1981-01-03", "age": 44}
        ]
        mock_add_item.return_value = "crocodile_data_entity_id"

        meta = {"token": "test_token"}
        data = {}

        asyncio.run(ingest_raw_data(meta, data))

        mock_add_item.assert_called_once_with(
            meta["token"], "crocodile_data", ENTITY_VERSION, mock_ingest_data.return_value
        )

    @patch("app_init.app_init.entity_service.add_item")
    def test_store_data_in_db(self, mock_add_item):
        mock_add_item.return_value = "crocodile_data_stored_id"

        meta = {"token": "test_token"}
        data = {
            "crocodile_data": {
                "technical_id": "crocodile_data_entity_id",
                "records": [{"id": 1, "name": "Bert", "sex": "M", "date_of_birth": "2010-06-27", "age": 14}]
            }
        }

        asyncio.run(store_data_in_db(meta, data))

        mock_add_item.assert_called_once_with(
            meta["token"], "crocodile_data", ENTITY_VERSION, data["crocodile_data"]
        )

if __name__ == "__main__":
    unittest.main()