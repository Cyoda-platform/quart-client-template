import logging
import asyncio
from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def schedule_data_ingestion_job(data):
    """
    Schedule a data ingestion job and save the job entity.
    """
    logger.info("Scheduling data ingestion job.")

    try:
        # Save the job entity to Cyoda
        job_entity_id = await entity_service.add_item(
            token=data["token"],
            entity_model="data_ingestion_job",
            entity_version=ENTITY_VERSION,
            entity=data
        )

        logger.info(f"Data ingestion job scheduled successfully with ID: {job_entity_id}")
    except Exception as e:
        logger.error(f"Error scheduling data ingestion job: {e}")
        raise


def main():
    """
    Entry point for the script.
    Defines the data model for the job entity and schedules the job.
    """
    # Example data model for the job entity
    job_data = {
        "job_id": "job_001",
        "pet_id": "7517577846774566682",
        "job_name": "Pet Data Ingestion Job",
        "scheduled_time": "2023-10-01T10:00:00Z",
        "status": "pending",
        "token": "test_token"  # Replace with a valid token
    }

    # Run the scheduling function
    asyncio.run(schedule_data_ingestion_job(job_data))


if __name__ == "__main__":
    main()
