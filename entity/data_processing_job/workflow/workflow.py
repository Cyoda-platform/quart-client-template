import logging
import unittest
from unittest.mock import patch, MagicMock
from common.app_init import entity_service
from common.connections import ingest_data, get_balance_responsible_parties
from common.config.config import ENTITY_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ingest_raw_data(meta, data):
    logger.info("Starting process to ingest raw data.")
    try:
        # Retrieve data from the external source
        response_data = ingest_data()
        # Save the raw data entity
        raw_data_entity_data = (
            response_data  # Assume it returns the correct data structure
        )
        entity_service.add_item(
            meta["token"], "raw_data_entity", ENTITY_VERSION, raw_data_entity_data
        )
        logger.info("Raw data entity saved successfully.")
    except Exception as e:
        logger.error(f"Error in ingest_raw_data: {e}")
        raise


def aggregate_raw_data(meta, data):
    logger.info("Starting process to aggregate raw data.")
    try:
        # Here you would perform aggregation logic
        aggregated_data = {
            "aggregated_key": "value"
        }  # Placeholder for the actual aggregation logic
        # Save the aggregated data entity
        aggregated_data_entity_data = aggregated_data
        entity_service.add_item(
            meta["token"],
            "aggregated_data_entity",
            ENTITY_VERSION,
            aggregated_data_entity_data,
        )
        logger.info("Aggregated data entity saved successfully.")
    except Exception as e:
        logger.error(f"Error in aggregate_raw_data: {e}")
        raise


def generate_and_send_report_email(meta, data):
    logger.info("Starting process to generate and send report email.")
    try:
        report_entity_data = {
            "report_id": "report_001",
            "generated_at": "2023-10-01T10:00:00Z",
            "report_title": "Monthly Data Analysis",
            "summary": {},
            "distribution_info": {},
        }
        # Save the report entity
        entity_service.add_item(
            meta["token"], "report_entity", ENTITY_VERSION, report_entity_data
        )
        logger.info("Report entity saved successfully.")
    except Exception as e:
        logger.error(f"Error in generate_and_send_report_email: {e}")
        raise


# Test classes
class TestDataProcessingJob(unittest.TestCase):
    @patch("common.app_init.entity_service.add_item")
    def test_ingest_raw_data(self, mock_entity_service):
        mock_entity_service.return_value = None
        meta = {"token": "test_token"}
        data = {}
        ingest_raw_data(meta, data)
        mock_entity_service.assert_called_once_with(
            meta["token"],
            "raw_data_entity",
            ENTITY_VERSION,
            mock_entity_service.return_value,
        )

    @patch("common.app_init.entity_service.add_item")
    def test_aggregate_raw_data(self, mock_entity_service):
        mock_entity_service.return_value = None
        meta = {"token": "test_token"}
        data = {}
        aggregate_raw_data(meta, data)
        mock_entity_service.assert_called_once_with(
            meta["token"],
            "aggregated_data_entity",
            ENTITY_VERSION,
            mock_entity_service.return_value,
        )

    @patch("common.app_init.entity_service.add_item")
    def test_generate_and_send_report_email(self, mock_entity_service):
        mock_entity_service.return_value = None
        meta = {"token": "test_token"}
        data = {}
        generate_and_send_report_email(meta, data)
        mock_entity_service.assert_called_once_with(
            meta["token"],
            "report_entity",
            ENTITY_VERSION,
            mock_entity_service.return_value,
        )


if __name__ == "__main__":
    unittest.main()
