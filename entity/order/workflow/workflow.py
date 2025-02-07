# Sure! Below is the implementation of the processor functions for handling orders: `save_order`, `confirm_order`, `process_payment`, and `notify_delivery`. I've reused existing functions and ensured dependent entities are saved as specified. I've also included test cases using mocks for external services to allow for isolated testing.
# 
# ```python
import json
import logging
import unittest
from unittest.mock import patch, AsyncMock

from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION
from common.service.trino_service import ingest_data as trino_ingest_data
from common.service.trino_service import run_sql_query

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Processor Functions

async def save_order(meta, data):
    """Save the new order."""
    try:
        # Save the order entity
        order_id = await entity_service.add_item(
            meta["token"], "order", ENTITY_VERSION, data
        )
        logger.info(f"Order saved successfully with ID: {order_id}")
        return order_id
    except Exception as e:
        logger.error(f"Error saving order: {e}")
        raise

async def confirm_order(meta, data):
    """Confirm the order with the restaurant."""
    try:
        order_id = data["id"]
        # Here you would typically call the restaurant's API to confirm the order
        # For this example, we just log the action
        logger.info(f"Order {order_id} confirmed with the restaurant.")
        return order_id
    except Exception as e:
        logger.error(f"Error confirming order: {e}")
        raise

async def process_payment(meta, data):
    """Process the payment for the confirmed order."""
    try:
        payment_data = {
            "order_id": data["id"],
            "customer_id": data["customer_id"],
            "amount": data["total_amount"],
            "currency": "USD",
            "payment_method": "credit_card",  # This could be dynamic based on data
        }
        
        # Save the payment entity
        payment_id = await entity_service.add_item(
            meta["token"], "payment", ENTITY_VERSION, payment_data
        )
        
        # Ingest data for payment
        await trino_ingest_data(meta, payment_data)
        
        logger.info(f"Payment processed successfully with ID: {payment_id}")
        return payment_id
    except Exception as e:
        logger.error(f"Error processing payment: {e}")
        raise

async def notify_delivery(meta, data):
    """Notify delivery personnel about the order."""
    try:
        delivery_data = {
            "order_id": data["id"],
            "delivery_person_id": "deliv123",  # This would typically come from your delivery service
            "customer_id": data["customer_id"],
            "restaurant_id": data["restaurant_id"],
            "delivery_address": data["delivery_address"],
            "delivery_status": "Out for delivery",
            "items": data["items"],
            "additional_notes": "Please ring the doorbell upon arrival."
        }

        # Save the delivery entity
        delivery_id = await entity_service.add_item(
            meta["token"], "delivery", ENTITY_VERSION, delivery_data
        )
        
        # Ingest data for delivery
        await trino_ingest_data(meta, delivery_data)

        logger.info(f"Delivery notified successfully with ID: {delivery_id}")
        return delivery_id
    except Exception as e:
        logger.error(f"Error notifying delivery: {e}")
        raise


# Tests

class TestOrderProcessors(unittest.TestCase):

    @patch("app_init.app_init.entity_service.add_item", new_callable=AsyncMock)
    async def test_save_order(self, mock_add_item):
        mock_add_item.return_value = "order001"
        meta = {"token": "test_token"}
        data = {
            "id": "order001",
            "customer_id": "cust123",
            "restaurant_id": "rest001",
            "total_amount": 33.97,
            "items": []
        }
        result = await save_order(meta, data)
        self.assertEqual(result, "order001")

    @patch("app_init.app_init.entity_service.add_item", new_callable=AsyncMock)
    async def test_confirm_order(self, mock_add_item):
        meta = {"token": "test_token"}
        data = {"id": "order001"}
        result = await confirm_order(meta, data)
        self.assertEqual(result, "order001")

    @patch("app_init.app_init.entity_service.add_item", new_callable=AsyncMock)
    @patch("common.service.trino_service.ingest_data", new_callable=AsyncMock)
    async def test_process_payment(self, mock_ingest_data, mock_add_item):
        mock_add_item.return_value = "pay001"
        meta = {"token": "test_token"}
        data = {
            "id": "order001",
            "customer_id": "cust123",
            "total_amount": 33.97
        }
        result = await process_payment(meta, data)
        self.assertEqual(result, "pay001")

    @patch("app_init.app_init.entity_service.add_item", new_callable=AsyncMock)
    @patch("common.service.trino_service.ingest_data", new_callable=AsyncMock)
    async def test_notify_delivery(self, mock_ingest_data, mock_add_item):
        mock_add_item.return_value = "deliv001"
        meta = {"token": "test_token"}
        data = {
            "id": "order001",
            "customer_id": "cust123",
            "restaurant_id": "rest001",
            "delivery_address": "123 Pizza St",
            "items": []
        }
        result = await notify_delivery(meta, data)
        self.assertEqual(result, "deliv001")

# Uncomment the line below to run the tests when this script is executed directly
if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Overview
# - The code defines four processor functions to handle order-related operations, ensuring they follow the business logic outlined in your requirements.
# - Each function logs its actions and handles any necessary data ingestion.
# - Tests are provided for each processor function using mocks for external services to ensure isolated testing.
# 
# Let me know if you need any modifications or further assistance!