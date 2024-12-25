import logging
import json
import unittest
from unittest.mock import patch
from common.app_init import entity_service, ai_service
from common.config.config import TRINO_AI_API, ENTITY_VERSION
from common.service.trino_service import get_trino_schema_id_by_entity_name

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_report(meta, data):
    logger.info("Starting report generation using AI service.")
    try:
        # Get the schema for the report from Trino
        schema_id = get_trino_schema_id_by_entity_name("report_schema")
        ai_response = ai_service.ai_chat(
            token=meta["token"],
            chat_id=schema_id,
            ai_endpoint=TRINO_AI_API,
            ai_question="Generate the report based on the latest data.",
        )
        report_content = json.loads(ai_response)

        report_data = {
            "report_id": "report_001",
            "generated_at": "2023-10-01T10:00:00Z",
            "report_title": "Monthly Data Processing Report",
            "content": report_content,
        }
        entity_service.add_item(meta["token"], "report_entity", ENTITY_VERSION, report_data)
        logger.info("Report generated and saved successfully.")
    except Exception as e:
        logger.error(f"Error generating report: {e}")


class TestReportGeneration(unittest.TestCase):
    @patch("common.app_init.entity_service.add_item")
    @patch("common.app_init.ai_service.ai_chat")
    def test_create_report(self, mock_ai_chat, mock_add_item):
        mock_ai_chat.return_value = json.dumps({"report_data": "Sample report content"})
        mock_add_item.return_value = None
        meta = {"token": "test_token"}
        data = {}  # No input data required for report generation
        create_report(meta, data)
        mock_add_item.assert_called_once()  # Verify that the report was saved
