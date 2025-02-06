# Here's the implementation of the processor function for adding a restaurant, named `add_restaurant_process`. I've reused the `ingest_data` function from `connections.py` and included test cases with mocks for external services.
# 
# ```python
# File: restaurant_processor.py

import asyncio
import logging
from logic.app_init import entity_service
from connections import connections

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_restaurant_process(meta, data):
    # Ingest raw data for the new restaurant
    raw_data_id = await connections.ingest_data(entity_name='restaurant', data=data)

    # Save the restaurant entity
    restaurant_entity = {
        "restaurantId": data["restaurant_id"],
        "name": data["name"],
        "menu": data["menu"],
        "location": data["location"],
        "contact_info": data["contact_info"],
        "opening_hours": data["opening_hours"],
        "raw_data_id": raw_data_id
    }
    
    await entity_service.add_item(restaurant_entity)
    logger.info(f"Restaurant added: {restaurant_entity}")

# Tests
import unittest
from unittest.mock import patch, AsyncMock

class TestRestaurantProcessor(unittest.TestCase):

    @patch('connections.connections.ingest_data', new_callable=AsyncMock)
    @patch('logic.app_init.entity_service.add_item', new_callable=AsyncMock)
    def test_add_restaurant_process(self, mock_add_item, mock_ingest_data):
        mock_ingest_data.return_value = "raw_data_123"
        data = {
            "restaurant_id": "R54321",
            "name": "Tasty Bites",
            "menu": [
                {
                    "item_id": "I001",
                    "item_name": "Burger",
                    "price": 8.99,
                    "availability": True
                }
            ],
            "location": {
                "address": "456 Elm St, Anytown, USA",
                "latitude": 40.712776,
                "longitude": -74.005974
            },
            "contact_info": {
                "phone": "555-123-4567",
                "email": "info@tastybites.com"
            },
            "opening_hours": {
                "monday": "11:00 AM - 10:00 PM",
                "tuesday": "11:00 AM - 10:00 PM"
            }
        }
        loop = asyncio.get_event_loop()
        loop.run_until_complete(add_restaurant_process({}, data))
        mock_add_item.assert_called_once()

if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Explanation
# - **Function**: The `add_restaurant_process` function ingests restaurant data, saves it as a raw data entity, and then creates the restaurant entity by calling the `add_item` method from the entity service.
# - **Logging**: Provided to track the addition of the restaurant entity.
# - **Tests**: The test for `add_restaurant_process` mocks both the `ingest_data` function and the `add_item` method. It verifies that the function processes the data correctly and interacts with the external services as intended.
# 
# This setup allows users to test the function in an isolated environment. Let me know if you need any adjustments or further explanations!