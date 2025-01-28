# ```python

import logging
import asyncio
from app_init.app_init import entity_service
from entity.pet_data_entity.connections.connections import ingest_data as ingest_raw_data
from common.config.config import ENTITY_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def retrieve_pet_process(meta, data):
    """Process to retrieve pet details from the Petstore API."""
    logger.info("Starting the process to retrieve pet details.")

    pet_id = data.get("pet_id")

    if not pet_id:
        logger.error("Pet ID is not provided.")
        raise ValueError("Pet ID must be provided to retrieve pet details.")

    # Call the existing ingest_data function to retrieve raw pet data
    raw_data = await ingest_raw_data(data["pet_id"])

    # Check if raw data is successfully retrieved
    if not raw_data:
        logger.error("No raw data received during ingestion.")
        raise ValueError("Failed to retrieve pet data from the API.")

    # Save the raw pet data to the pet_data_entity
    pet_data_entity_id = await entity_service.add_item(
        meta["token"],
        "pet_data_entity",
        ENTITY_VERSION,
        raw_data
    )

    data["pet_data_entity"] = {"technical_id": pet_data_entity_id}
    logger.info(f"Pet data entity saved successfully with ID: {pet_data_entity_id}")


# Unit Tests
import unittest
from unittest.mock import patch


class TestRetrievePetProcess(unittest.TestCase):

    @patch("app_init.app_init.entity_service.add_item")
    @patch("workflow.ingest_raw_data")
    def test_retrieve_pet_process_success(self, mock_ingest_data, mock_add_item):
        # Arrange
        mock_ingest_data.return_value = {
            "id": "7517577846774566682",
            "name": "G5q#z:_jJRWm6Vm.g`v1xMri0cBv[V]#GCcM",
            "category": {
                "id": "4328014582300286193",
                "name": "r"
            },
            "photoUrls": [
                "-R)Kse7Nq3qsffCK-c3K",
                "e&_oHQ2Ig<kBHl}#sU24j"
            ],
            "tags": [
                {
                    "id": "7911873500464509041",
                    "name": "G5q#z:_jJRWm6Vm.g`v1xMri0cBv[V]#GCcM"
                }
            ],
            "status": "sold"
        }
        mock_add_item.return_value = "pet_data_entity_id"
        meta = {"token": "test_token"}
        data = {"pet_id": "7517577846774566682"}

        # Act
        asyncio.run(retrieve_pet_process(meta, data))

        # Assert
        mock_ingest_data.assert_called_once_with(data["pet_id"])
        mock_add_item.assert_called_once_with(
            meta["token"],
            "pet_data_entity",
            ENTITY_VERSION,
            mock_ingest_data.return_value
        )
        self.assertIn("pet_data_entity", data)
        self.assertEqual(data["pet_data_entity"]["technical_id"], "pet_data_entity_id")


if __name__ == "__main__":
    unittest.main()
# ```