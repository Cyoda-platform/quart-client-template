import logging
import json
import os
from common.app_init import entity_service, ai_service
from common.config.config import ENTITY_VERSION, TRINO_AI_API
from common.service.trino_service import get_trino_schema_id_by_entity_name
from common.util.utils import read_json_file, parse_json
from entity.raw_data_entity.connections.connections import ingest_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ingest_data_process(meta, data):
    logger.info("Starting process to ingest raw data.")
    try:
        response_data = ingest_data(
            data["request_parameters"]["code"],
            data["request_parameters"]["country"],
            data["request_parameters"]["name"],
        )
        raw_data_entity_data = (
            response_data  # Assuming it returns the correct data structure
        )
        raw_data_entity_id = entity_service.add_item(
            meta["token"], "raw_data_entity", ENTITY_VERSION, raw_data_entity_data
        )
        data.setdefault("raw_data_entity", {})["technical_id"] = raw_data_entity_id
        logger.info("Raw data entity saved successfully.")
    except Exception as e:
        logger.error(f"Error in ingest_data_process: {e}")
        raise


def aggregate_raw_data_process(meta, data):
    logger.info("Starting process to aggregate raw data.")
    try:
        base_dir = os.path.abspath(os.path.join(__file__, "../../../"))
        aggregated_data_entity_path = os.path.join(
            base_dir, "aggregated_data_entity", "aggregated_data_entity.json"
        )
        aggregated_data_entity_schema = read_json_file(aggregated_data_entity_path)
        aggregated_data = ai_service.ai_chat(
            token=meta["token"],
            chat_id=get_trino_schema_id_by_entity_name("raw_data_entity"),
            ai_endpoint=TRINO_AI_API,
            ai_question=f"Could you please return json report based on this schema: {json.dumps(aggregated_data_entity_schema)}. Return only json",
        )
        aggregated_data_entity_data = json.loads(parse_json(aggregated_data))
        aggregated_data_entity_id = entity_service.add_item(
            meta["token"],
            "aggregated_data_entity",
            ENTITY_VERSION,
            aggregated_data_entity_data,
        )
        data.setdefault("aggregated_data_entity", {})[
            "technical_id"
        ] = aggregated_data_entity_id
        logger.info("Aggregated data entity saved successfully.")
    except Exception as e:
        logger.error(f"Error in aggregate_raw_data_process: {e}")
        raise


def generate_report_process(meta, data):
    logger.info("Starting process to generate and send report email.")
    try:
        aggregated_data_entity = entity_service.get_item(
            meta["token"],
            "aggregated_data_entity",
            ENTITY_VERSION,
            data.get("aggregated_data_entity").get("technical_id"),
        )
        report_entity_data = {
            "report_id": "report_001",
            "generated_at": "2023-10-01T10:00:00Z",
            "report_title": "Monthly Data Analysis",
            "summary": aggregated_data_entity,
            "distribution_info": {},
        }
        report_entity_id = entity_service.add_item(
            meta["token"], "report_entity", ENTITY_VERSION, report_entity_data
        )
        logger.info(f"Report entity saved successfully: {report_entity_id}")
        logger.info(f"Sending email with report {report_entity_id}")
    except Exception as e:
        logger.error(f"Error in generate_report_process: {e}")
        raise


# Tests with mocks
import unittest
from unittest.mock import patch


class TestDataProcessingJob(unittest.TestCase):
    @patch("common.app_init.entity_service.add_item")
    @patch("entity.raw_data_entity.connections.connections.ingest_data")
    def test_ingest_data_process(self, mock_ingest_data, mock_entity_service):
        mock_ingest_data.return_value = [
            {
                "brpCode": "7080005051286",
                "brpName": "Example Name",
                "country": "FI",
                "businessId": "123456789",
                "codingScheme": "GS1",
                "validityStart": "2023-01-01",
                "validityEnd": "2025-01-01",
            }
        ]
        mock_entity_service.return_value = "raw_data_entity_id"
        meta = {"token": "test_token"}
        data = {
            "request_parameters": {"code": "7080005051286", "country": "FI", "name": ""}
        }
        ingest_data_process(meta, data)
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
                    "validityEnd": "2025-01-01",
                }
            ],
        )

    @patch("common.app_init.entity_service.add_item")
    @patch("common.app_init.ai_service.ai_chat")
    @patch("common.service.trino_service.get_trino_schema_id_by_entity_name")
    def test_aggregate_raw_data_process(
        self, mock_get_trino_schema, mock_ai_chat, mock_entity_service
    ):
        mock_ai_chat.return_value = '{"aggregated_data": "dummy_aggregated_data"}'
        mock_entity_service.return_value = "aggregated_data_entity_id"
        mock_get_trino_schema.return_value = "response_data_entity_id"
        aggregated_data_entity_schema = {"schema": "dummy_schema"}

        def mock_read_json_file(path):
            return aggregated_data_entity_schema

        def mock_parse_json(data):
            return data

        meta = {"token": "test_token"}
        data = {}
        aggregate_raw_data_process(meta, data)

    @patch("common.app_init.entity_service.add_item")
    @patch("common.app_init.entity_service.get_item")
    def test_generate_report_process(self, mock_get_item, mock_entity_service):
        mock_get_item.return_value = {"aggregated_data": "dummy_data"}
        mock_entity_service.return_value = "report_entity_id"
        meta = {"token": "test_token"}
        data = {"aggregated_data_entity": {"technical_id": "aggregated_data_entity_id"}}
        generate_report_process(meta, data)
        mock_get_item.assert_called_once_with(
            meta["token"],
            "aggregated_data_entity",
            ENTITY_VERSION,
            "aggregated_data_entity_id",
        )
        mock_entity_service.assert_called_once_with(
            meta["token"],
            "report_entity",
            ENTITY_VERSION,
            {
                "report_id": "report_001",
                "generated_at": "2023-10-01T10:00:00Z",
                "report_title": "Monthly Data Analysis",
                "summary": {"aggregated_data": "dummy_data"},
                "distribution_info": {},
            },
        )


if __name__ == "__main__":
    unittest.main()
