# ```python
import asyncio
import logging
import unittest
from unittest.mock import patch

from app_init.app_init import entity_service
from common.service.connections.connections import ingest_data as ingest_raw_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ingest_raw_data(meta, data) -> str:
    """
    Ingest raw data from the external data source and add the RAW_DATA entity.
    
    Args:
        meta: Metadata containing authentication tokens.
        data: The data related to the data_ingestion_job entity.
    
    Returns:
        str: The ID of the added RAW_DATA entity.
    """
    try:
        # Call the ingest_data function to fetch raw data from the API.
        raw_data = await ingest_raw_data()
        if not raw_data:
            logger.error("No raw data received for ingestion.")
            return

        raw_data_entity = {
            "id": raw_data[0]["id"],
            "name": raw_data[0]["name"],
            "slug": raw_data[0]["slug"],
            "parent_id": raw_data[0]["parent_id"],
            "sub_categories": raw_data[0]["sub_categories"]
        }

        # Save the RAW_DATA entity using the entity service.
        raw_data_id = await entity_service.add_item(
            meta["token"],
            "raw_data_entity",
            "1.0",
            raw_data_entity
        )
        return raw_data_id
    except Exception as e:
        logger.error(f"Error in ingest_raw_data: {e}")
        raise

class TestDataIngestionJob(unittest.TestCase):

    @patch("app_init.app_init.entity_service.add_item")
    def test_ingest_raw_data_success(self, mock_add_item):
        mock_add_item.return_value = "raw_data_id"
        meta = {"token": "test_token"}
        data = {
            "job_id": "job_001",
            "name": "Data Ingestion Job",
            "scheduled_time": "2023-10-01T10:00:00Z",
            "status": "completed",
            "raw_data_entity": None  # Placeholder for the raw data entity
        }

        result = asyncio.run(ingest_raw_data(meta, data))
        self.assertEqual(result, "raw_data_id")
        mock_add_item.assert_called_once_with(
            meta["token"],
            "raw_data_entity",
            "1.0",
            {
                "id": "01JKR602ZXDRRXNZ1M5Y1T4496",
                "name": "Hand Tools",
                "slug": "hand-tools",
                "parent_id": None,
                "sub_categories": [
                    {
                        "id": "01JKR60308DYZWDKN07F15F1MS",
                        "name": "Hammer",
                        "slug": "hammer",
                        "parent_id": "01JKR602ZXDRRXNZ1M5Y1T4496",
                        "sub_categories": []
                    },
                    {
                        "id": "01JKR60308DYZWDKN07F15F1MT",
                        "name": "Hand Saw",
                        "slug": "hand-saw",
                        "parent_id": "01JKR602ZXDRRXNZ1M5Y1T4496",
                        "sub_categories": []
                    }
                ]
            }
        )

if __name__ == "__main__":
    unittest.main()
# ```