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
        "job_id": "job_20231011",
        "job_name": "Data Processing Job - Sample",
        "scheduled_time": "2023-10-11T17:00:00Z",
        "status": "pending",
        "start_time": "2023-10-11T17:00:00Z",
        "end_time": "2023-10-11T17:30:00Z",
        "total_records_processed": 200,
        "successful_records": 190,
        "failed_records": 10,
        "failure_reason": ["Timeout", "Data format error"],
        "summary": {
            "average_processing_time_ms": 300,
            "max_processing_time_ms": 600,
            "min_processing_time_ms": 150,
        },
        "data_source": {
            "source_name": "External API",
            "source_url": "https://api.opendata.esett.com/EXP01/BalanceResponsibleParties",
            "data_retrieval_method": "GET",
        },
        "request_parameters": {
            "code": "7080005051286",
            "country": "FI",
            "name": "Energi Vannkraft AS",
        },
        "recipients": [{"name": "Admin User", "email": "admin@example.com"}],
    }

    try:
        token = authenticate()
        result = data_processing_job_scheduler(token, test_data)
        print(f"Job scheduled successfully. Job details: {result}")
    except Exception as e:
        print(f"Error scheduling job: {str(e)}")


if __name__ == "__main__":
    main()
