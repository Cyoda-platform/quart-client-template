# ```python
import logging
import asyncio
from app_init.app_init import entity_service
from entity.pet_details_entity.connections.connections import ingest_data as ingest_raw_data  # Reusing existing ingest_data function

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ingest_pet_process(meta, data):
    """
    Process to ingest pet details from the API and save to pet_details_entity.
    """
    try:
        # Extracting statuses from the incoming data
        statuses = ["available", "pending", "sold"]

        # Initialize list to hold all pet details
        all_pet_details = []

        for status in statuses:
            # Ingest data for each status using the existing ingest_data function
            pet_data = await ingest_raw_data(status)

            if pet_data:
                all_pet_details.extend(pet_data)

        # Save the pet details to the pet_details_entity
        if all_pet_details:
            pet_details_entity_id = await entity_service.add_item(
                meta["token"], "pet_details_entity", "1.0", all_pet_details
            )
            logger.info(f"Pet details entity saved successfully with ID: {pet_details_entity_id}")
        else:
            logger.warning("No pet details found to save.")

    except Exception as e:
        logger.error(f"Error in ingest_pet_process: {e}")
        raise

# Testing with Mocks
import unittest
from unittest.mock import patch

class TestPetDetailsJob(unittest.TestCase):

    @patch("app_init.app_init.entity_service.add_item")
    @patch("workflow.ingest_raw_data")
    def test_ingest_pet_process(self, mock_ingest_raw_data, mock_add_item):
        # Mocking the ingest_data function to return dummy data
        mock_ingest_raw_data.side_effect = [
            [{"id": 1, "status": "available"}],  # For available
            [{"id": 2, "status": "pending"}],    # For pending
            [{"id": 3, "status": "sold"}]        # For sold
        ]
        mock_add_item.return_value = "pet_details_entity_id"

        meta = {"token": "test_token"}
        data = {"id": "job_001"}

        asyncio.run(ingest_pet_process(meta, data))

        # Verify that the add_item was called with the correct parameters
        mock_add_item.assert_called_once_with(
            meta["token"], "pet_details_entity", "1.0", 
            [{"id": 1, "status": "available"}, 
             {"id": 2, "status": "pending"}, 
             {"id": 3, "status": "sold"}]
        )

if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Explanation:
# 1. **Function `ingest_pet_process`**:
#    - This function ingests pet details by calling the reused `ingest_data` function for each status ("available", "pending", and "sold").
#    - It collects all pet details and saves them to `pet_details_entity` using the `entity_service.add_item` method.
# 
# 2. **Testing**:
#    - The unit tests use `unittest` and `unittest.mock` to mock the external service calls.
#    - It verifies that the `add_item` method is called with the correct arguments after data ingestion.
# 
# This setup allows users to test the ingestion process in an isolated environment without relying on actual services, ensuring the integrity of the code.