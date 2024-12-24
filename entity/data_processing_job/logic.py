import logging

from common.config.config import ENTITY_VERSION
from common.app_init import entity_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def data_processing_job_scheduler(token: str, data: dict) -> dict:
    # Save a job entity with data model $data to cyoda
    job_entity = entity_service.add_item(
        token, "data_processing_job", ENTITY_VERSION, data
    )
    return job_entity


# Test Code
import unittest
from unittest.mock import MagicMock


class TestDataProcessingJobScheduler(unittest.TestCase):
    def setUp(self):
        self.mock_service = MagicMock(spec=entity_service)
        self.scheduler = data_processing_job_scheduler(self.mock_service)

    def test_schedule_job(self):
        token = "my_token"
        test_data = {
            "job_id": "job_001",
            "job_name": "Data Processing Job",
            "scheduled_time": "2023-10-01T17:00:00Z",
            "status": "completed",
            "start_time": "2023-10-01T17:00:00Z",
            "end_time": "2023-10-01T17:30:00Z",
            "total_records_processed": 150,
            "successful_records": 145,
            "failed_records": 5,
            "failure_reason": ["Timeout", "Data format error"],
            "summary": {
                "average_processing_time_ms": 250,
                "max_processing_time_ms": 500,
                "min_processing_time_ms": 100,
            },
            "data_source": {
                "source_name": "External API",
                "source_url": "https://api.example.com/data",
                "data_retrieval_method": "GET",
            },
            "request_parameters": {
                "param1": "value1",
                "param2": "value2",
                "param3": "value3",
            },
            "recipients": [
                {"name": "Admin User", "email": "admin@example.com"},
                {"name": "Data Analyst", "email": "analyst@example.com"},
            ],
            "report": {
                "report_id": "report_001",
                "generated_at": "2023-10-01T17:35:00Z",
                "report_title": "Monthly Data Processing Report",
                "distribution_info": {
                    "sent_at": "2023-10-01T17:40:00Z",
                    "communication_method": "Email",
                },
            },
        }
        self.mock_service.add_item.return_value = test_data

        result = self.scheduler.schedule_job(token, test_data)

        self.mock_service.add_item.assert_called_once_with(
            token, "data_processing_job", ENTITY_VERSION, test_data
        )
        self.assertEqual(result, test_data)


if __name__ == "__main__":
    unittest.main()
