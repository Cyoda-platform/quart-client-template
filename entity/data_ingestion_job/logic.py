from common.app_init import entity_service
from common.auth.auth import authenticate


def data_ingestion_job_scheduler(token: str, data: dict) -> dict:
    # Save a job entity with data model $data to cyoda
    job_entity = entity_service.add_item(
        token, "data_ingestion_job", ENTITY_VERSION, data
    )
    return job_entity


def main():
    # Test data for the job scheduler
    test_data = {
        "job_id": "job_001",
        "job_name": "Data Ingestion Job",
        "status": "scheduled",
        "data_source": {
            "source_name": "External API",
            "data_retrieval_method": "GET",
            "source_url": "https://api.example.com/data",
        },
        "request_parameters": {
            "code": "BRP12345",
            "country": "FI",
            "name": "Sample BRP",
        },
    }

    token = authenticate()  # Get authentication token
    data_ingestion_job_scheduler(token, test_data)  # Schedule the job


if __name__ == "__main__":
    main()
