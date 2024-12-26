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
        "failure_reason": ["Network error", "Invalid data format"],
        "summary": {
            "average_processing_time_ms": 300,
            "max_processing_time_ms": 600,
            "min_processing_time_ms": 150,
        },
        "data_source": {
            "source_name": "External Database",
            "source_url": "https://api.example.com/database",
            "data_retrieval_method": "POST",
        },
        "request_parameters": {
            "param1": "value1",
            "param2": "value2",
            "param3": "value3",
        },
        "recipients": [
            {"name": "System Admin", "email": "sysadmin@example.com"},
            {"name": "Data Engineer", "email": "dataengineer@example.com"},
        ],
        "report": {
            "report_id": "report_002",
            "generated_at": None,
            "report_title": "Daily Data Ingestion Report",
            "distribution_info": {"sent_at": None, "communication_method": "Email"},
        },
    }

    try:
        token = authenticate()
        result = data_ingestion_job_scheduler(token, test_data)
        print(f"Job scheduled successfully. Job details: {result}")
    except Exception as e:
        print(f"Error scheduling job: {str(e)}")


if __name__ == "__main__":
    main()
