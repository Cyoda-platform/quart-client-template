import logging
import unittest
from unittest.mock import patch

from common.app_init import entity_service
from common.config.config import ENTITY_VERSION
from entity.raw_data_entity.connections.connections import ingest_raw_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ingest_data(meta, data):
    logger.info("Starting data ingestion process.")
    try:
        code = data["request_parameters"]["code"]
        country = data["request_parameters"]["country"]
        name = data["request_parameters"]["name"]
        # Call the external API to retrieve data
        raw_data = ingest_raw_data(code, country, name)
        # Save the raw data to the raw_data_entity
        raw_data_entity_data = []
        for item in raw_data:
            raw_data_entity_data.append({
                    "brpCode": item.get("brpCode"),
                    "brpName": item.get("brpName"),
                    "country": item.get("country"),
                    "businessId": item.get("businessId"),
                    "codingScheme": item.get("codingScheme"),
                    "validityStart": item.get("validityStart"),
                    "validityEnd": item.get("validityEnd"),
                })
        entity_service.add_item(
            meta["token"], "raw_data_entity", ENTITY_VERSION, raw_data_entity_data
        )
        logger.info("Data ingestion complete. Raw data saved successfully.")
    except Exception as e:
        logger.error(f"Error during data ingestion: {e}")
        raise


class TestDataIngestionJob(unittest.TestCase):
    @patch("workflow.ingest_raw_data")
    @patch("common.app_init.entity_service.add_item")  # Inner decorator
    def test_ingest_data(self, mock_entity_service, mock_ingest_raw_data):
        # Arrange
        mock_ingest_raw_data.return_value = [
            {
                "brpCode": "7080005051286",
                "brpName": "Example Name",
                "country": "FI",
                "businessId": "123456789",
                "codingScheme": "GS1",
                "validityStart": "2023-01-01",
                "validityEnd": "2025-01-01"
            }
        ]
        mock_entity_service.return_value = "raw_data_entity_id"

        meta = {"token": "test_token"}
        data = {
            "request_parameters": {
                "code": "7080005051286",
                "country": "FI",
                "name": ""
            }
        }

        # Act
        ingest_data(meta, data)

        # Assert
        mock_entity_service.assert_called_once_with(
            meta["token"],
            "raw_data_entity",
            ENTITY_VERSION,
            [
                {
                    "brpCode": "7080005051286",
                    "brpName": "Example Name",
                    "country": "FI",
                    "businessId": "123456789",
                    "codingScheme": "GS1",
                    "validityStart": "2023-01-01",
                    "validityEnd": "2025-01-01"
                }
            ]
        )

if __name__ == "__main__":
    unittest.main()