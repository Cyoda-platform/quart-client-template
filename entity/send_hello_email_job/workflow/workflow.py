import logging
import unittest
from unittest.mock import patch
from common.app_init import entity_service
from common.config.config import ENTITY_VERSION

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
        # Assume email sent successfully
        logger.info("Email sent successfully.")
    except Exception as e:
        logger.error(f"Error in send_email_process: {e}")
        raise


# Test example with mocks
class TestSendEmailProcess(unittest.TestCase):
    @patch("common.app_init.entity_service.add_item")
    def test_send_email_process(self, mock_entity_service):
        mock_entity_service.return_value = None
        meta = {"token": "test_token"}
        data = {
            "entity": {
                "email_details": {
                    "recipient": "recipient@example.com",
                    "subject": "Hello!",
                    "body": "This is a test email.",
                    "attachments": [],
                }
            }
        }
        send_email_process(meta, data)
        logger.info("Test completed successfully.")


if __name__ == "__main__":
    unittest.main()
