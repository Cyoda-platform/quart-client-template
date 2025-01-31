# Here’s the updated scheduler file for the `crocodile_data_ingestion_job`, incorporating the filter suggestions provided by the user. This file includes a function to save a job entity with the specified data model and a main function for end-to-end testing.
# 
# ```python
import logging
import asyncio
from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def schedule_crocodile_data_ingestion_job(data):
    """Schedule a crocodile data ingestion job and save the job entity."""
    logger.info("Scheduling crocodile data ingestion job.")
    
    try:
        # Save the job entity to Cyoda
        job_entity_id = await entity_service.add_item(
            token=data["token"],
            entity_model="crocodile_data_ingestion_job",
            entity_version=ENTITY_VERSION,
            entity=data
        )
        
        logger.info(f"Crocodile data ingestion job scheduled successfully with ID: {job_entity_id}")
    except Exception as e:
        logger.error(f"Error scheduling crocodile data ingestion job: {e}")
        raise

def main():
    # Example data model for the job entity
    job_data = {
        "job_id": "ingestion_job_001",
        "job_name": "Daily Crocodile Data Ingestion",
        "api_url": "https://test-api.k6.io/public/crocodiles/",
        "parameters": {
            "filter_by_name": ["F", "M"],  # Filter by names starting with 'F' or 'M'
            "filter_by_age": {
                "min": 0,  # Minimum age
                "max": 200  # Maximum age
            }
        },
        "last_run": "2023-10-01T05:00:00Z",
        "status": "pending",
        "ingestion_attempts": 0,
        "execution_log": [],
        "scheduled_time": "2023-10-01T05:00:00Z",
        "created_by": "admin_user@example.com",
        "created_at": "2023-09-30T12:00:00Z",
        "token": "test_token"  # Add the necessary token for authentication
    }
    
    # Run the scheduling function
    asyncio.run(schedule_crocodile_data_ingestion_job(job_data))

if __name__ == "__main__":
    main()
# ```
# 
# ### Explanation of the Code:
# 1. **`schedule_crocodile_data_ingestion_job` Function**:
#    - This asynchronous function schedules a crocodile data ingestion job according to the details provided in the `data` parameter.
#    - It logs the scheduling process and saves the job entity to Cyoda without executing any additional logic.
# 
# 2. **`main` Function**:
#    - Acts as the entry point of the script.
#    - Defines the `job_data` model, which now includes the filtering criteria specified by the user:
#      - **`filter_by_name`**: A list containing "F" or "M" to filter names accordingly.
#      - **`filter_by_age`**: A dictionary containing minimum and maximum age values (0 and 200, respectively).
#    - Calls the `schedule_crocodile_data_ingestion_job` function to perform the scheduling.
# 
# 3. **Entry Point**:
#    - The script checks if it is being run directly and invokes the `main` function to initiate the scheduling.
# 
# This scheduler allows users to test the crocodile data ingestion job scheduling and confirm that the job entity is saved in the Cyoda system with the specified filters. If you have more adjustments or questions, let me know! 😊