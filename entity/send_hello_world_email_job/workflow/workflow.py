import logging
import unittest
from unittest.mock import patch
from common.config.config import ENTITY_VERSION
from common.app_init import entity_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def send_email_process(meta, data):
    logger.info("Starting process to send email.")
    try:
        email_details = data["entity"]["email_details"]
        # Simulate sending email (you can integrate with your email service)
        logger.info(
            f"Sending email to {email_details['recipient']} with subject: {email_details['subject']}"
        )
        # Assume email sent successfully, now save email_entity
        email_entity_data = {
            "id": "email-12345",
            "recipient": email_details["recipient"],
            "subject": email_details["subject"],
            "body": email_details["body"],
            "sent_timestamp": "2023-10-10T17:00:00Z",
            "status": "sent",
        }
        entity_service.add_item(
            meta["token"], "email_entity", ENTITY_VERSION, email_entity_data
        )
        logger.info("Email entity saved successfully.")
    except Exception as e:
        logger.error(f"Error in send_email_process: {e}")
        raise


class TestSendEmailProcess(unittest.TestCase):
    # This is correct mock, common.app_init.entity_service without .add_item will not work!
    @patch("common.app_init.entity_service.add_item")
    def test_send_email_process(self, mock_entity_service):
        mock_entity_service.return_value = None
        meta = {"token": "test_token"}
        data = {
            "entity": {
                "email_details": {
                    "recipient": "recipient@example.com",
                    "subject": "Hello World",
                    "body": "This is a test email.",
                    "attachments": [],
                }
            }
        }
        send_email_process(meta, data)
        mock_entity_service.assert_called_once()


# Uncomment the line below to run the tests when this script is executed directly
if __name__ == "__main__":
    unittest.main()
