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
        "job_id": "job_002",
        "job_name": "Data Ingestion Job",
        "scheduled_time": "2023-10-02T09:00:00Z",
        "status": "in_progress",
        "start_time": "2023-10-02T09:00:00Z",
        "end_time": None,
        "total_records_processed": 200,
        "successful_records": 195,
        "failed_records": 5,
        "failure_reason": ["Network issue", "Invalid data format"],
        "summary": {
            "average_processing_time_ms": 300,
            "max_processing_time_ms": 600,
            "min_processing_time_ms": 150,
        },
        "data_source": {
            "source_name": "Internal Database",
            "source_url": "https://internal.api.example.com/data",
            "data_retrieval_method": "POST",
        },
        "request_parameters": {
            "param1": "valueA",
            "param2": "valueB",
            "param3": "valueC",
        },
        "recipients": [
            {"name": "Data Manager", "email": "manager@example.com"},
            {"name": "Support Team", "email": "support@example.com"},
        ],
    }

    try:
        token = authenticate()
        result = data_ingestion_job_scheduler(token, test_data)
        print(f"Job scheduled successfully. Job details: {result}")
    except Exception as e:
        print(f"Error scheduling job: {str(e)}")


if __name__ == "__main__":
    main()
