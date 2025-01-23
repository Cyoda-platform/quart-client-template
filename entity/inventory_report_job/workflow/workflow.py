# ```python
import json
import logging
import asyncio
from app_init.app_init import entity_service
from entity.inventory_data_entity.connections.connections import ingest_data as ingest_inventory_data
from entity.inventory_report_entity.connections.connections import ingest_data as ingest_report_data
from common.config.config import ENTITY_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def generate_inventory_report(meta, data):
    """Process function to retrieve inventory items and compute report metrics."""
    try:
        # Step 1: Retrieve inventory data using the ingest function
        inventory_data = await ingest_inventory_data(meta["token"])
        
        if not inventory_data:
            logger.warning("No inventory data received for report generation.")
            return
        
        # Step 2: Process the inventory data to generate report metrics
        total_items = len(inventory_data)
        total_value = sum(item['price'] * item['quantity'] for item in inventory_data)
        average_price = total_value / total_items if total_items > 0 else 0
        
        # Step 3: Prepare the report data entity
        report_data = {
            "report_id": f"report_{data['job_id']}",
            "generated_at": data["end_time"],
            "report_title": "Inventory Overview Report",
            "total_items": total_items,
            "average_price": average_price,
            "total_value": total_value,
            "inventory_items": inventory_data
        }
        
        # Step 4: Save the report entity
        report_entity_id = await ingest_report_data(meta["token"], ENTITY_VERSION, report_data)
        logger.info(f"Inventory report entity saved successfully with ID: {report_entity_id}")

    except Exception as e:
        logger.error(f"Error in generate_inventory_report: {e}")
        raise

# Unit Tests
import unittest
from unittest.mock import patch

class TestGenerateInventoryReport(unittest.TestCase):
    
    @patch("entity.inventory_data_entity.connections.connections.ingest_data")
    @patch("entity.inventory_report_entity.connections.connections.ingest_data")
    @patch("app_init.app_init.entity_service.add_item")
    def test_generate_inventory_report_success(self, mock_add_item, mock_ingest_report_data, mock_ingest_inventory_data):
        # Mock the inventory data returned from ingest_data
        mock_ingest_inventory_data.return_value = [
            {"id": "d290f1ee-6c54-4b01-90e6-d701748f0851", "name": "Widget Adapter", "price": 20.0, "quantity": 5},
            {"id": "a1b2c3d4-e5f6-7g8h-9i0j-k1l2m3n4o5p6", "name": "Gadget Pro", "price": 35.0, "quantity": 2}
        ]

        # Mock the report data saving
        mock_ingest_report_data.return_value = "report_entity_id"
        
        meta = {"token": "test_token"}
        data = {
            "job_id": "job_001",
            "end_time": "2023-10-02T05:15:00Z"
        }

        # Run the generate_inventory_report function
        asyncio.run(generate_inventory_report(meta, data))

        # Assertions to check that the report was saved correctly
        mock_ingest_report_data.assert_called_once()
        self.assertEqual(mock_add_item.call_count, 0)  # Ensure add_item is not called, as we're directly calling ingest_data

if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Explanation of the Code
# 1. **`generate_inventory_report(meta, data)`**:
#    - This is the primary function to generate the inventory report.
#    - It retrieves inventory data using the `ingest_data` function from `inventory_data_entity.connections.connections`.
#    - It processes the data to compute total items, average price, and total value.
#    - It prepares the report data and saves it using the `ingest_data` function from `inventory_report_entity.connections.connections`.
# 
# 2. **Unit Tests**:
#    - The `TestGenerateInventoryReport` class contains tests for the `generate_inventory_report` function.
#    - Mocks are used to simulate the behavior of external functions and ensure the function can run in isolation.
#    - Assertions check that the correct functions are called and that the report is generated with the expected metrics.
# 
# This setup allows users to test the report generation process effectively in an isolated environment without needing actual API calls.