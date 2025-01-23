# ```python
import asyncio
import logging
import aiohttp
from app_init.app_init import entity_service
from common.service.trino_service import run_sql_query

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def search_flights(meta, data):
    """Trigger the flight search based on user input."""
    logger.info("Starting flight search process.")
    try:
        # Construct the API query based on user input
        departure_airport = data["departure_airport"]
        arrival_airport = data["arrival_airport"]
        departure_date = data["travel_dates"]["departure_date"]
        return_date = data["travel_dates"]["return_date"]
        passengers = data["number_of_passengers"]

        # Query the Airport Gap API to get flight details
        async with aiohttp.ClientSession() as session:
            api_url = f"https://airportgap.com/api/airports/search?departure={departure_airport}&arrival={arrival_airport}&departure_date={departure_date}&return_date={return_date}&passengers={passengers}"
            async with session.get(api_url) as response:
                if response.status == 200:
                    flight_data = await response.json()
                    
                    # Save the flight results to flight_results_entity
                    flight_results_id = await entity_service.add_item(
                        meta["token"], "flight_results_entity", "1.0", flight_data
                    )
                    data["flight_results_entity"] = {"technical_id": flight_results_id}
                    logger.info(f"Flight results saved with ID: {flight_results_id}")
                else:
                    logger.warning("No flights found in the response.")
                    await notify_no_flights(meta, data)
    except Exception as e:
        logger.error(f"Error in search_flights: {e}")
        await handle_api_error(meta, data)


async def notify_no_flights(meta, data):
    """Notify the user that no flights were found."""
    logger.info("Notifying user that no flights were found.")
    try:
        notification_data = {
            "notification_id": "notification_001",
            "message": "No flights were found matching your search criteria.",
            "search_criteria": {
                "departure_airport": data["departure_airport"],
                "arrival_airport": data["arrival_airport"],
                "travel_dates": data["travel_dates"],
                "number_of_passengers": data["number_of_passengers"],
            },
            "timestamp": "2023-10-01T10:05:00Z",  # Replace with current timestamp
            "user_contact": {
                "email": "user@example.com",  # This should be dynamically retrieved
                "phone": "+1234567890"  # This should be dynamically retrieved
            },
            "suggestions": [
                "Try adjusting your travel dates.",
                "Consider searching from nearby airports.",
                "Check back later for updated flight availability."
            ]
        }

        # Save the no_flight_notification_entity
        no_flight_notification_id = await entity_service.add_item(
            meta["token"], "no_flight_notification_entity", "1.0", notification_data
        )
        data["no_flight_notification_entity"] = {"technical_id": no_flight_notification_id}
        logger.info(f"No flight notification saved with ID: {no_flight_notification_id}")
    except Exception as e:
        logger.error(f"Error in notify_no_flights: {e}")
        raise


async def handle_api_error(meta, data):
    """Handle errors that occur during the API call."""
    logger.info("Handling API error during flight search.")
    try:
        error_data = {
            "notification_id": "error_notification_001",
            "timestamp": "2023-10-01T12:00:00Z",  # Replace with current timestamp
            "status": "error",
            "message": "An error occurred while trying to fetch flight data from the Airport Gap API.",
            "details": {
                "error_code": "API_CALL_FAILURE",
                "failed_request": {
                    "url": "https://airportgap.com/api/airports",
                    "method": "GET"
                },
                "retry_suggestion": "Please try again later or check your internet connection."
            },
            "user_notification": {
                "user_id": data["user_id"],
                "email": "user@example.com",  # This should be dynamically retrieved
                "notification_sent": True
            }
        }

        # Save the error_notification_entity
        error_notification_id = await entity_service.add_item(
            meta["token"], "error_notification_entity", "1.0", error_data
        )
        data["error_notification_entity"] = {"technical_id": error_notification_id}
        logger.info(f"Error notification saved with ID: {error_notification_id}")
    except Exception as e:
        logger.error(f"Error in handle_api_error: {e}")
        raise


# Testing with Mocks
import unittest
from unittest.mock import patch

class TestFlightSearchJob(unittest.TestCase):

    @patch("aiohttp.ClientSession.get")
    @patch("app_init.app_init.entity_service.add_item")
    async def test_search_flights_success(self, mock_add_item, mock_get):
        # Setup
        mock_get.return_value.__aenter__.return_value.status = 200
        mock_get.return_value.__aenter__.return_value.json = asyncio.Future()
        mock_get.return_value.__aenter__.return_value.json.set_result({"data": []})

        mock_add_item.return_value = "flight_results_id"

        meta = {"token": "test_token"}
        data = {
            "departure_airport": "JFK",
            "arrival_airport": "LAX",
            "travel_dates": {
                "departure_date": "2023-12-01",
                "return_date": "2023-12-10"
            },
            "number_of_passengers": 2
        }

        # Execute
        await search_flights(meta, data)

        # Assertions
        mock_add_item.assert_called_once_with(
            meta["token"], "flight_results_entity", "1.0", {"data": []}
        )

    @patch("app_init.app_init.entity_service.add_item")
    async def test_notify_no_flights(self, mock_add_item):
        meta = {"token": "test_token"}
        data = {
            "departure_airport": "JFK",
            "arrival_airport": "LAX",
            "travel_dates": {
                "departure_date": "2023-12-01",
                "return_date": "2023-12-10"
            },
            "number_of_passengers": 2,
            "user_id": "user_123"
        }

        await notify_no_flights(meta, data)

        mock_add_item.assert_called_once_with(
            meta["token"], "no_flight_notification_entity", "1.0", {
                "notification_id": "notification_001",
                "message": "No flights were found matching your search criteria.",
                "search_criteria": {
                    "departure_airport": "JFK",
                    "arrival_airport": "LAX",
                    "travel_dates": {
                        "departure": "2023-12-01",
                        "return": "2023-12-10"
                    },
                    "number_of_passengers": 2
                },
                "timestamp": "2023-10-01T10:05:00Z",
                "user_contact": {
                    "email": "user@example.com",
                    "phone": "+1234567890"
                },
                "suggestions": [
                    "Try adjusting your travel dates.",
                    "Consider searching from nearby airports.",
                    "Check back later for updated flight availability."
                ]
            }
        )

    @patch("app_init.app_init.entity_service.add_item")
    async def test_handle_api_error(self, mock_add_item):
        meta = {"token": "test_token"}
        data = {
            "user_id": "user_123"
        }

        await handle_api_error(meta, data)

        mock_add_item.assert_called_once_with(
            meta["token"], "error_notification_entity", "1.0", {
                "notification_id": "error_notification_001",
                "timestamp": "2023-10-01T12:00:00Z",
                "status": "error",
                "message": "An error occurred while trying to fetch flight data from the Airport Gap API.",
                "details": {
                    "error_code": "API_CALL_FAILURE",
                    "failed_request": {
                        "url": "https://airportgap.com/api/airports",
                        "method": "GET"
                    },
                    "retry_suggestion": "Please try again later or check your internet connection."
                },
                "user_notification": {
                    "user_id": "user_123",
                    "email": "user@example.com",
                    "notification_sent": True
                }
            }
        )

if __name__ == "__main__":
    unittest.main()
# ``` 
# 
# ### Explanation of the Code
# 1. **Processor Functions**:
#    - **search_flights**: This function queries the Airport Gap API with user-specified parameters and saves the results in `flight_results_entity`. If no flights are found, it calls `notify_no_flights`.
#    - **notify_no_flights**: This function creates a notification if no flights are found and saves it in `no_flight_notification_entity`.
#    - **handle_api_error**: This function creates an error notification in case of issues during the API call and saves it in `error_notification_entity`.
# 
# 2. **Unit Tests**:
#    - The tests use mocking to simulate responses from the API and the entity service. It tests the key functionalities of each processor function to ensure they behave as expected without needing real API calls or database operations.
# 
# This setup allows for isolated testing of the functions, making it simpler to validate their logic and behavior during development.