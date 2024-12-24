import logging

from common.config.config import ENTITY_VERSION
from common.service.entity_service_interface import EntityService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SendHelloWorldEmailJobScheduler:
    def __init__(self, entity_service: EntityService):
        self.entity_service = entity_service

    def schedule_job(self, token: str, data: dict) -> dict:
        # Save a job entity with data model $data to cyoda
        job_entity = self.entity_service.add_item(
            token, "send_hello_world_email_job", ENTITY_VERSION, data
        )
        return job_entity


# Test Code
import unittest
from unittest.mock import MagicMock


class TestSendHelloWorldEmailJobScheduler(unittest.TestCase):
    def setUp(self):
        self.mock_service = MagicMock(spec=EntityService)
        self.scheduler = SendHelloWorldEmailJobScheduler(self.mock_service)

    def test_schedule_job(self):
        token = "my_token"
        test_data = {
            "job_id": "job_20231012",
            "status": "scheduled",
            "scheduled_time": "2023-10-12T17:00:00Z",
            "email_details": {
                "recipient": "mockuser@example.com",
                "subject": "Hello World from Mock Data",
                "body": "This is a mock email generated for testing purposes.",
                "attachments": [
                    {
                        "file_name": "sample_attachment.txt",
                        "file_size": 1024,
                        "file_type": "text/plain",
                    }
                ],
            },
            "created_timestamp": "2023-10-12T12:00:00Z",
            "last_modified_timestamp": "2023-10-12T12:00:00Z",
            "error_count": 0,
            "execution_details": {
                "start_time": None,
                "end_time": None,
                "execution_status": "pending",
            },
        }
        self.mock_service.add_item.return_value = test_data

        result = self.scheduler.schedule_job(token, test_data)

        self.mock_service.add_item.assert_called_once_with(
            token, "send_hello_world_email_job", ENTITY_VERSION, test_data
        )
        self.assertEqual(result, test_data)


if __name__ == "__main__":
    unittest.main()
