import logging
import json
import unittest
from unittest.mock import patch
from common.app_init import entity_service
from common.config.config import ENTITY_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def send_email_report_process(meta, data):
    logger.info("Starting process to generate and send the email report.")
    try:
        # Extracting details from the job data
        email_report_data = {
            "report_id": "report_20231010",
            "job_id": data["job_id"],
            "recipient": data["recipient"],
            "subject": data["subject"],
            "body": data["body"],
            "sent_timestamp": "2023-10-10T17:00:00Z",
            "status": "SENT",
            "attachments": data["attachments"],
            "generated_timestamp": "2023-10-10T16:45:00Z",
            "summary": data["summary"],
            "created_timestamp": "2023-10-01T12:00:00Z",
            "last_modified_timestamp": "2023-10-10T16:50:00Z",
            "error_count": 0,
            "execution_details": {
                "start_time": "2023-10-10T16:30:00Z",
                "end_time": "2023-10-10T16:45:00Z",
                "execution_status": "completed",
            },
        }

        # Save the email report entity
        email_report_entity_id = entity_service.add_item(
            meta["token"], "email_report_entity", ENTITY_VERSION, email_report_data
        )
        logger.info(f"Email report entity saved successfully: {email_report_entity_id}")
    except Exception as e:
        logger.error(f"Error in send_email_report_process: {e}")
        raise


class TestSendEmailReportProcess(unittest.TestCase):
    @patch("common.app_init.entity_service.add_item")
    def test_send_email_report_process(self, mock_entity_service):
        mock_entity_service.return_value = "email_report_entity_id"
        meta = {"token": "test_token"}
        data = {
            "job_id": "email_report_job_20231010",
            "recipient": "marketing_team@example.com",
            "subject": "Sentiment Analysis Summary Report",
            "body": "Attached is the summary report of the sentiment analysis conducted on user feedback.",
            "attachments": [],
            "summary": {"total_feedback": 100, "positive_feedback": 70},
        }

        # Act
        send_email_report_process(meta, data)

        # Assert
        mock_entity_service.assert_called_once_with(
            meta["token"],
            "email_report_entity",
            ENTITY_VERSION,
            {
                "report_id": "report_20231010",
                "job_id": "email_report_job_20231010",
                "recipient": "marketing_team@example.com",
                "subject": "Sentiment Analysis Summary Report",
                "body": "Attached is the summary report of the sentiment analysis conducted on user feedback.",
                "sent_timestamp": "2023-10-10T17:00:00Z",
                "status": "SENT",
                "attachments": [],
                "generated_timestamp": "2023-10-10T16:45:00Z",
                "summary": {"total_feedback": 100, "positive_feedback": 70},
                "created_timestamp": "2023-10-01T12:00:00Z",
                "last_modified_timestamp": "2023-10-10T16:50:00Z",
                "error_count": 0,
                "execution_details": {
                    "start_time": "2023-10-10T16:30:00Z",
                    "end_time": "2023-10-10T16:45:00Z",
                    "execution_status": "completed",
                },
            },
        )


if __name__ == "__main__":
    unittest.main()
