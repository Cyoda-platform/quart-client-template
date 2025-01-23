# ```python
import asyncio
import logging
import aiohttp
import unittest
from unittest.mock import patch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL = "https://fakerestapi.azurewebsites.net/api/v1/Authors"

async def fetch_data():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(API_URL, headers={"accept": "text/plain; v=1.0"}) as response:
                if response.status == 200:
                    return await response.json()
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
            "id": author["id"],
            "first_name": author["firstName"],
            "last_name": author["lastName"],
            "id_book": author["idBook"]
        } for author in data
    ]

    return mapped_data

class TestDataIngestion(unittest.TestCase):

    @patch("aiohttp.ClientSession.get")
    def test_ingest_data_success(self, mock_get):
        # Mock the API response
        mock_get.return_value.__aenter__.return_value.status = 200
        mock_get.return_value.__aenter__.return_value.json = asyncio.Future()
        mock_get.return_value.__aenter__.return_value.json.set_result([
            {"id": 1, "idBook": 1, "firstName": "First Name 1", "lastName": "Last Name 1"},
            {"id": 2, "idBook": 1, "firstName": "First Name 2", "lastName": "Last Name 2"}
        ])

        # Run the ingest_data function
        result = asyncio.run(ingest_data())

        # Assertions to check that data is mapped correctly
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["first_name"], "First Name 1")
        self.assertEqual(result[0]["last_name"], "Last Name 1")
        self.assertEqual(result[1]["id"], 2)
        self.assertEqual(result[1]["first_name"], "First Name 2")
        self.assertEqual(result[1]["last_name"], "Last Name 2")
    
    @patch("aiohttp.ClientSession.get")
    def test_ingest_data_failure(self, mock_get):
        # Mock the API response failure
        mock_get.return_value.__aenter__.return_value.status = 404
        
        # Run the ingest_data function
        result = asyncio.run(ingest_data())
        
        # Assertions to check that no data is received
        self.assertEqual(result, [])

if __name__ == "__main__":
    unittest.main()
# ``` 
# 
# ### Explanation of the Code
# 1. **`fetch_data()` Function**: 
#    - This asynchronous function makes a GET request to the specified API URL to retrieve author data.
#    - If the request is successful (HTTP status 200), it returns the JSON response.
#    - If there’s an error, it logs the error message.
# 
# 2. **`ingest_data()` Function**: 
#    - This public function retrieves the data using `fetch_data()`.
#    - If data is received, it maps the raw data to the required entity structure matching the expected format.
#    - Finally, it returns the mapped data.
# 
# 3. **Unit Tests**: 
#    - The class `TestDataIngestion` uses the `unittest` framework and mocks the API response using `unittest.mock`.
#    - The `test_ingest_data_success` method simulates a successful API response and verifies that the data is mapped correctly.
#    - The `test_ingest_data_failure` method simulates a failure scenario and ensures that the function behaves as expected, returning an empty list.
# 
# This setup allows for testing the data ingestion process effectively in an isolated environment without needing actual API calls.