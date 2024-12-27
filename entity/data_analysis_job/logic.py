import logging

from common.auth.auth import authenticate
from common.config.config import ENTITY_VERSION
from common.app_init import entity_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def data_analysis_job_scheduler(token: str, data: dict) -> dict:
    # Save a job entity with data model $data to cyoda
    job_entity = entity_service.add_item(
        token, "data_analysis_job", ENTITY_VERSION, data
    )
    return job_entity


def main():
    # Test data for the job scheduler
    test_token = "test_token_123"
    test_data = {
        "job_id": "job_20231010",
        "status": "scheduled",
        "scheduled_time": "2023-10-10T17:00:00Z",
        "data_source": {
            "source_url": "https://api.example.com/data",
            "retrieval_method": "GET",
            "parameters": {"param1": "value1", "param2": "value2"},
        },
        "execution_details": {
            "start_time": None,
            "end_time": None,
            "execution_status": "pending",
        },
        "report_summary": {
            "total_records_processed": 0,
            "successful_records": 0,
            "failed_records": 0,
            "failure_reasons": [],
        },
    }

    try:
        token = authenticate()
        result = data_analysis_job_scheduler(token, test_data)
        print(f"Job scheduled successfully. Job details: {result}")
    except Exception as e:
        print(f"Error scheduling job: {str(e)}")


if __name__ == "__main__":
    main()
