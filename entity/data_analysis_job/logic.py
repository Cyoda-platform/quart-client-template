# ```python
import logging
from common.app_init import entity_service
from common.config.config import ENTITY_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def schedule_data_analysis_job(data: dict) -> dict:
    """
    Schedule a data analysis job and save it as a job entity in Cyoda.
    
    Args:
        data (dict): The job data to be saved.

    Returns:
        dict: The created job entity.
    """
    job_entity = entity_service.add_item(
        "test_token",  # Replace with actual authentication token
        "data_analysis_job",
        ENTITY_VERSION,
        data
    )
    logger.info(f"Data analysis job scheduled successfully with ID: {job_entity['job_id']}")
    return job_entity

def main():
    # Sample job data to be saved
    job_data = {
        "job_id": "job_001",
        "job_name": "London Houses Data Analysis",
        "scheduled_time": "2023-10-01T09:00:00Z",
        "status": "scheduled",
        "data_source": {
            "source_name": "London Houses CSV",
            "source_url": "https://raw.githubusercontent.com/Cyoda-platform/cyoda-ai/refs/heads/ai-2.x/data/test-inputs/v1/connections/london_houses.csv",
            "data_retrieval_method": "GET"
        },
        "analysis_summary": {
            "average_price": None,
            "median_price": None,
            "max_price": None,
            "min_price": None,
            "total_houses": 0,
            "analysis_date": "2023-10-01"
        },
        "recipients": [
            {
                "name": "Admin User",
                "email": "admin@example.com"
            }
        ]
    }

    try:
        job_entity = schedule_data_analysis_job(job_data)
        print(f"Job scheduled: {job_entity}")
    except Exception as e:
        print(f"Error scheduling job: {str(e)}")

if __name__ == "__main__":
    main()
# ```
# 
# ### Explanation
# - **schedule_data_analysis_job**: This function takes in the job data and saves it as a job entity in Cyoda using the `entity_service.add_item` method. It logs the success message with the job ID.
#   
# - **main Function**: The `main` function initializes the job data with sample values and calls the `schedule_data_analysis_job` function. It includes error handling for any exceptions that may occur during the job scheduling process.
# 
# - **Entry Point**: The `if __name__ == "__main__":` block serves as the entry point for the script, enabling end-to-end testing of the scheduling functionality. The user can run this script directly to test scheduling a data analysis job.