# ```python
import asyncio
import logging
import aiohttp
import unittest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL = "https://fakerestapi.azurewebsites.net/api/v1/Users"

async def fetch_data():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(API_URL, headers={"accept": "text/plain; v=1.0"}) as response:
                if response.status == 200:
                    return await response.json()  # Fetch JSON response
                else:
                    logger.error(f"Error fetching data: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Exception occurred: {str(e)}")
            return None

async def ingest_data() -> list:
    data = await fetch_data()
    if data is None:
        logger.error("No data received for ingestion.")
        return []

    # Map raw data to the entity structure
    mapped_data = [
        {
            "id": user["id"],
            "user_name": user["userName"],
            # Excluded password for security best practices
        } for user in data
    ]

    return mapped_data

from unittest.mock import patch, AsyncMock

class TestDataIngestion(unittest.TestCase):

    @patch("aiohttp.ClientSession.get")
    def test_ingest_data_success(self, mock_get):
        # Mock API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = [
            {"id": 1, "userName": "User 1"},
            {"id": 2, "userName": "User 2"}
        ]
        mock_get.return_value.__aenter__.return_value = mock_response

        # Run the ingest_data function
        result = asyncio.run(ingest_data())

        # Assertions
        self.assertTrue(len(result) > 0)  # Ensure data was received
        self.assertIn("id", result[0])  # Check for 'id' field
        self.assertIn("user_name", result[0])  # Check for 'user_name' field
        self.assertEqual(result[0]["user_name"], "User 1")  # Verify first user name
        self.assertEqual(result[1]["user_name"], "User 2")  # Verify second user name

    @patch("aiohttp.ClientSession.get")
    def test_fetch_data_error_handling(self, mock_get):
        # Mock API error response
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.json.return_value = None
        mock_get.return_value.__aenter__.return_value = mock_response

        # Run the ingest_data function
        result = asyncio.run(ingest_data())

        # Assertions
        self.assertEqual(result, [])  # Ensure no data is returned on error


if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Explanation of the Code
# 
# 1. **`fetch_data()` Function**:
#    - This asynchronous function sends a GET request to the specified API URL to retrieve user data.
#    - If the request is successful (HTTP status 200), it returns the JSON response.
#    - If there’s an error in fetching the data, it logs the error and returns `None`.
# 
# 2. **`ingest_data()` Function**:
#    - This public function calls `fetch_data()` to retrieve the data.
#    - If data is received, it maps the raw data to a specified entity structure, renaming fields as necessary.
#    - The password field is excluded for security reasons.
#    - Finally, it returns the mapped data.
# 
# 3. **Unit Tests**:
#    - The `TestDataIngestion` class uses the `unittest` framework to test the functionality of the `ingest_data()` function.
#    - The `test_ingest_data_success` method checks if the data is correctly mapped and contains expected values.
#    - The `test_fetch_data_error_handling` method simulates an error by altering the API URL to an invalid endpoint and checks if the response is handled appropriately.
# 
# This setup allows users to test the data ingestion process effectively in an isolated environment without needing actual API calls.