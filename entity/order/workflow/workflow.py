import json
import logging
import unittest
from unittest.mock import patch, AsyncMock
import asyncio
import aiohttp

from app_init.app_init import entity_service
from common.config.config import ENTITY_VERSION
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

        logger.info(f"Delivery notified successfully with ID: {delivery_id}")
        return delivery_id
    except Exception as e:
        logger.error(f"Error notifying delivery: {e}")
        raise


# Tests

class TestOrderProcessors(unittest.TestCase):

    @patch("app_init.app_init.entity_service.add_item", new_callable=AsyncMock)
    def test_save_order(self, mock_add_item):
        mock_add_item.return_value = "order001"
        meta = {"token": "test_token"}
        data = {
            "id": "order001",
            "customer_id": "cust123",
            "restaurant_id": "rest001",
            "total_amount": 33.97,
            "items": []
        }
        result = asyncio.run(save_order(meta, data))
        self.assertEqual(result, "order001")

    @patch("app_init.app_init.entity_service.add_item", new_callable=AsyncMock)
    def test_confirm_order(self, mock_add_item):
        meta = {"token": "test_token"}
        data = {"id": "order001"}
        result = asyncio.run(confirm_order(meta, data))
        self.assertEqual(result, "order001")

    @patch("app_init.app_init.entity_service.add_item", new_callable=AsyncMock)
    def test_process_payment(self, mock_add_item):
        mock_add_item.return_value = "pay001"
        meta = {"token": "test_token"}
        data = {
            "id": "order001",
            "customer_id": "cust123",
            "total_amount": 33.97
        }
        result = asyncio.run(process_payment(meta, data))
        self.assertEqual(result, "pay001")

    @patch("app_init.app_init.entity_service.add_item", new_callable=AsyncMock)
    def test_notify_delivery(self, mock_add_item):
        mock_add_item.return_value = "deliv001"
        meta = {"token": "test_token"}
        data = {
            "id": "order001",
            "customer_id": "cust123",
            "restaurant_id": "rest001",
            "delivery_address": "123 Pizza St",
            "items": []
        }
        result = asyncio.run(notify_delivery(meta, data))
        self.assertEqual(result, "deliv001")

if __name__ == "__main__":
    unittest.main()