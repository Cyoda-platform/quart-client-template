import logging
import json
import unittest
from unittest.mock import patch

from common.app_init import entity_service, ai_service
from common.config.config import ENTITY_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_and_analyze_feedback_process(meta, data):
    logger.info("Starting process to fetch and analyze user feedback.")
    feedback_data = []
    try:
        # Fetch user feedback. Use open api document to implement data ingestion
        feedback_data = [
            {"id": "1", "comment": "Love the new features!", "createdAt": "2023-09-30T10:00:00Z"},
            {"id": "2", "comment": "Could improve the loading times.", "createdAt": "2023-09-30T11:00:00Z"}
        ]
        logger.info(f"Fetched user feedback: {feedback_data}")

        # Analyze sentiment of the feedback
        comments = [entry['comment'] for entry in feedback_data]
        sentiment_analysis_result = ai_service.ai_chat(
            token=meta["token"],
            chat_id="sentiment_analysis_id",  # Placeholder chat ID
            ai_endpoint="sentiment",
            ai_question=json.dumps({"comments": comments})
        )
        logger.info(f"Sentiment analysis result: {sentiment_analysis_result}")

        # Construct report entity
        report_entity_data = {
            "report": f"Sentiment analysis: {sentiment_analysis_result}"
        }
        # Save report entity
        report_entity_id = entity_service.add_item(
            meta["token"], "report_entity", ENTITY_VERSION, report_entity_data
        )
        logger.info(f"Report entity saved successfully: {report_entity_id}")
    except Exception as e:
        logger.error(f"Error in fetch_and_analyze_feedback_process: {e}")
        raise

class TestFetchAndAnalyzeFeedbackProcess(unittest.TestCase):
    @patch("common.app_init.entity_service.add_item")
    @patch("common.app_init.ai_service.ai_chat")
    def test_fetch_and_analyze_feedback_process(self, mock_ai_chat, mock_entity_service):
        mock_ai_chat.return_value = {"positive": 3, "negative": 1, "neutral": 1}
        mock_entity_service.return_value = "report_entity_id"
        meta = {"token": "test_token"}
        data = {}

        # Act
        fetch_and_analyze_feedback_process(meta, data)

        # Assert
        mock_entity_service.assert_called_once_with(
            meta["token"],
            "report_entity",
            ENTITY_VERSION,
            {"report": "Sentiment analysis: {\"positive\": 3, \"negative\": 1, \"neutral\": 1}"}
        )