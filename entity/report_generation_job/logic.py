# ```python
import logging
from common.auth.auth import authenticate
from common.config.config import ENTITY_VERSION
from common.app_init import entity_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def schedule_report_generation_job(data: dict) -> dict:
    """Save a job entity with the data model to Cyoda."""
    job_entity = entity_service.add_item(
        data["token"], "report_generation_job", ENTITY_VERSION, data
    )
    return job_entity

def main():
    # Example data for the report generation job
    test_data = {
        "job_id": "job_12345",
        "job_name": "Daily Inventory Report Generation",
        "scheduled_time": "2023-10-02T08:00:00Z",
        "status": "scheduled",
        "filters_used": {
            "category": "Electronics",
            "in_stock": True
        }
    }

    try:
        token = authenticate()
        test_data["token"] = token  # Add the token to the test data
        result = schedule_report_generation_job(test_data)
        print(f"Report generation job scheduled successfully. Job details: {result}")
    except Exception as e:
        print(f"Error scheduling job: {str(e)}")

if __name__ == "__main__":
    main()
# ```
# 
# This code snippet provides a scheduler function, `schedule_report_generation_job`, that saves a job entity to Cyoda using the provided data. The `main` function serves as an entry point for end-to-end testing, allowing the user to run the function and verify that the job is scheduled successfully.