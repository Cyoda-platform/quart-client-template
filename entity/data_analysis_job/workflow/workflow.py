import logging
import json
import os
import unittest
from unittest.mock import patch
from common.app_init import entity_service, ai_service
from common.config.config import ENTITY_VERSION, TRINO_AI_API
from common.service.trino_service import get_trino_schema_id_by_entity_name
from common.util.utils import read_json_file, parse_json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_and_analyze_data(meta, data):
    logger.info("Starting process to download and analyze data.")
    try:
        # Retrieve the data source URL and parameters
        data_source = data["entity"]["data_source"]
        source_url = data_source["source_url"]
        params = data_source.get("parameters", {})

        # Simulate data retrieval (implement actual retrieval logic as needed)
        logger.info(f"Downloading data from {source_url} with parameters: {params}")
        # Assume data is downloaded and saved as data_content
        data_content = (
            "{" "data" " : [{" "example_key" " : " "example_value" "}]}"
        )  # Mock data

        # Perform analysis on the downloaded data (implement actual analysis logic)
        logger.info("Analyzing downloaded data.")
        analysis_result = json.loads(data_content)

        # Prepare aggregated data entity
        aggregated_data_entity_data = {
            "report_summary": analysis_result,
            "generated_at": "2023-10-01T10:00:00Z",
        }

        # Save the aggregated data entity
        aggregated_data_entity_id = entity_service.add_item(
            meta["token"],
            "data_report_entity",
            ENTITY_VERSION,
            aggregated_data_entity_data,
        )
        logger.info(
            f"Aggregated data entity saved successfully with ID: {aggregated_data_entity_id}"
        )
    except Exception as e:
        logger.error(f"Error in download_and_analyze_data: {e}")
        raise


class TestDownloadAndAnalyzeData(unittest.TestCase):
    @patch("common.app_init.entity_service.add_item")  # Mock entity_service.add_item
    def test_download_and_analyze_data(self, mock_entity_service):
        mock_entity_service.return_value = "aggregated_data_entity_id"
        meta = {"token": "test_token"}
        data = {
            "entity": {
                "data_source": {
                    "source_url": "https://api.example.com/data",
                    "parameters": {"param1": "value1"},
                }
            }
        }

        # Act
        download_and_analyze_data(meta, data)

        # Assert
        mock_entity_service.assert_called_once_with(
            meta["token"],
            "data_report_entity",
            ENTITY_VERSION,
            {
                "report_summary": {"data": [{"example_key": "example_value"}]},
                "generated_at": "2023-10-01T10:00:00Z",
            },
        )


if __name__ == "__main__":
    unittest.main()
