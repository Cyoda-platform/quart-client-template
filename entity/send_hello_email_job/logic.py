import logging

from common.config.config import ENTITY_VERSION
from common.app_init import entity_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def send_hello_email_job_scheduler(token: str, data: dict) -> dict:
    # Save a job entity with data model $data to cyoda
    job_entity = entity_service.add_item(
        token, "send_hello_email_job", ENTITY_VERSION, data
    )
    return job_entity


def main():
    # Test data for the job scheduler
    test_token = "test_token_123"
    test_data = {
        "job_id": "job_002",
        "job_name": "Send Hello Email Job",
        "scheduled_time": "2023-10-02T09:00:00Z",
        "status": "completed",
        "start_time": "2023-10-02T09:00:00Z",
        "end_time": "2023-10-02T09:00:30Z",
        "recipients": [
            {"name": "John Doe", "email": "john.doe@example.com"},
            {"name": "Jane Smith", "email": "jane.smith@example.com"},
        ],
        "email_subject": "Hello!",
        "email_body": "Hello! This is a test email sent by the Send Hello Email Job.",
        "attempts": 1,
        "failure_reason": null,
    }

    try:
        result = send_hello_email_job_scheduler(test_token, test_data)
        print(f"Job scheduled successfully. Job details: {result}")
    except Exception as e:
        print(f"Error scheduling job: {str(e)}")


if __name__ == "__main__":
    main()
