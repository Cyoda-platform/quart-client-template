import logging

from common.auth.auth import authenticate
from common.config.config import ENTITY_VERSION
from common.app_init import entity_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def data_ingestion_job_scheduler(token: str, data: dict) -> dict:
    # Save a job entity with data model $data to cyoda
    job_entity = entity_service.add_item(
        token, "data_ingestion_job", ENTITY_VERSION, data
    )
    return job_entity


def main():
    # Test data for the job scheduler
    test_token = "test_token_123"
    test_data = {
        "job_id": "job_12345",
        "status": "completed",
        "start_time": "2023-10-05T10:00:00Z",
        "end_time": "2023-10-05T11:30:00Z",
        "raw_entity_id": "",
        "aggregated_entity_id": "",
        "parameters": {"country": "FI", "code": "", "name": ""},
    }

    try:
        token = authenticate()
        result = data_ingestion_job_scheduler(token, test_data)
        print(f"Job scheduled successfully. Job details: {result}")
    except Exception as e:
        print(f"Error scheduling job: {str(e)}")


if __name__ == "__main__":
    main()
