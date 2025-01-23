import logging
import asyncio
from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def schedule_inventory_report_job(data):
    """Schedule the inventory report job and save the job entity."""
    logger.info("Scheduling inventory report job.")

    try:
        # Save the job entity to Cyoda
        job_entity_id = await entity_service.add_item(
            token=data["token"],
            entity_model="inventory_report_job",
            entity_version=ENTITY_VERSION,
            entity=data
        )

        logger.info(f"Inventory report job scheduled successfully with ID: {job_entity_id}")
    except Exception as e:
        logger.error(f"Error scheduling inventory report job: {e}")
        raise

def main():
    # Example data model for the job entity
    job_data = {
        "job_id": "job_001",
        "job_name": "Daily Inventory Report Generation",
        "scheduled_time": "2023-10-02T05:00:00Z",
        "status": "scheduled",
        "token": "test_token"  # Add the necessary token for authentication
    }

    # Run the scheduling function
    asyncio.run(schedule_inventory_report_job(job_data))

if __name__ == "__main__":
    main()
