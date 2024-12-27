import logging
import unittest
from unittest.mock import patch
from common.config.config import ENTITY_VERSION
from common.app_init import entity_service
from entity.raw_data_entity.connections.connections import ingest_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ingest_data_process(meta, data):
    logger.info("Starting process to ingest raw data.")
    try:
        request_params = data.get("request_parameters", {})
        response_data = ingest_data(
            code=request_params.get("code"),
            country=request_params.get("country"),
            name=request_params.get("name"),
        )
        raw_data_entity_id = entity_service.add_item(
            meta["token"], "raw_data_entity", ENTITY_VERSION, response_data
        )
        data.setdefault("raw_data_entity", {})["technical_id"] = raw_data_entity_id
        logger.info("Raw data entity saved successfully.")
    except Exception as e:
        logger.error(f"Error in ingest_data_process: {e}")
        raise


def aggregate_data_process(meta, data):
    logger.info("Starting process to aggregate raw data.")
    try:
        raw_data_entity = entity_service.get_item(
            meta["token"],
            "raw_data_entity",
            ENTITY_VERSION,
            data["raw_data_entity"]["technical_id"],
        )
        # Example aggregation logic (replace with actual logic)
        aggregated_data = {
            "summary": {
                "total_records": len(raw_data_entity),
                "successful_records": len(raw_data_entity),
                "failed_records": 0,
            }
        }
        aggregated_data_entity_id = entity_service.add_item(
            meta["token"], "aggregated_data_entity", ENTITY_VERSION, aggregated_data
        )
        data.setdefault("aggregated_data_entity", {})[
            "technical_id"
        ] = aggregated_data_entity_id
        logger.info("Aggregated data entity saved successfully.")
    except Exception as e:
        logger.error(f"Error in aggregate_data_process: {e}")
        raise


def send_email_process(meta, data):
    logger.info("Starting process to send email.")
    try:
        aggregated_data_entity = entity_service.get_item(
            meta["token"],
            "aggregated_data_entity",
            ENTITY_VERSION,
            data["aggregated_data_entity"]["technical_id"],
        )
        # Example email sending logic (replace with actual logic)
        logger.info(f"Sending email with aggregated data: {aggregated_data_entity}")
        logger.info("Email sent successfully.")
    except Exception as e:
        logger.error(f"Error in send_email_process: {e}")
        raise


# Test classes with mocks
class TestDataIngestionJobProcessors(unittest.TestCase):

    @patch("common.app_init.entity_service.add_item")
    @patch("entity.raw_data_entity.connections.connections.ingest_data")
    def test_ingest_data_process(self, mock_ingest_data, mock_add_item):
        mock_ingest_data.return_value = [
            {"brpCode": "579000282425", "brpName": "42 Renaissance ApS"}
        ]
        mock_add_item.return_value = "raw_data_entity_id"
        meta = {"token": "test_token"}
        data = {
            "request_parameters": {"code": "579000282425", "country": "DK", "name": ""}
        }
        ingest_data_process(meta, data)
        mock_ingest_data.assert_called_once()
        mock_add_item.assert_called_once()

    @patch("common.app_init.entity_service.add_item")
    @patch("common.app_init.entity_service.get_item")
    def test_aggregate_data_process(self, mock_get_item, mock_add_item):
        mock_get_item.return_value = [
            {"brpCode": "579000282425", "brpName": "42 Renaissance ApS"}
        ]
        mock_add_item.return_value = "aggregated_data_entity_id"
        meta = {"token": "test_token"}
        data = {"raw_data_entity": {"technical_id": "raw_data_entity_id"}}
        aggregate_data_process(meta, data)
        mock_get_item.assert_called_once()
        mock_add_item.assert_called_once()

    @patch("common.app_init.entity_service.get_item")
    def test_send_email_process(self, mock_get_item):
        mock_get_item.return_value = {
            "summary": {
                "total_records": 1,
                "successful_records": 1,
                "failed_records": 0,
            }
        }
        meta = {"token": "test_token"}
        data = {"aggregated_data_entity": {"technical_id": "aggregated_data_entity_id"}}
        send_email_process(meta, data)
        mock_get_item.assert_called_once()


if __name__ == "__main__":
    unittest.main()
