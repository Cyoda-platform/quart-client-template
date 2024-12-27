import logging

from common.auth.auth import authenticate
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


def main():
    # Test data for the job scheduler
    test_token = "test_token_123"
    test_data = {
        "job_id": "job_002",
        "job_name": "Monthly Data Aggregation Job",
        "scheduled_time": "2023-11-01T00:00:00Z",
        "status": "pending",
        "start_time": None,
        "end_time": None,
        "total_records_processed": 0,
        "successful_records": 0,
        "failed_records": 0,
        "failure_reason": [],
        "summary": {
            "average_processing_time_ms": 0,
            "max_processing_time_ms": 0,
            "min_processing_time_ms": 0,
        },
        "data_source": {
            "source_name": "Internal Database",
            "source_url": "https://internal-db.example.com/data",
            "data_retrieval_method": "SQL Query",
        },
        "request_parameters": {
            "query": "SELECT * FROM energy_consumption WHERE month = '2023-10'",
            "limit": 1000,
        },
        "recipients": [
            {"name": "Data Analyst", "email": "analyst@example.com"},
            {"name": "System Admin", "email": "admin@example.com"},
        ],
    }

    try:
        token = authenticate()
        result = data_processing_job_scheduler(token, test_data)
        print(f"Job scheduled successfully. Job details: {result}")
    except Exception as e:
        print(f"Error scheduling job: {str(e)}")


if __name__ == "__main__":
    main()
