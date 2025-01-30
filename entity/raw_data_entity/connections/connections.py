# Here's the Python code to fetch data from the specified external data source, process it according to the required entity structure, and return the mapped data. I'll also include tests to ensure the functionality works as intended.
# 
# ```python
import asyncio
import logging
import aiohttp
import unittest

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
            "id": author.get("id", 0),
            "idBook": author.get("idBook", 0),
            "firstName": author.get("firstName", "string"),
            "lastName": author.get("lastName", "string")
        } for author in data
    ]
    
    return mapped_data

# Unit Tests
class TestDataIngestion(unittest.TestCase):

    def test_ingest_data_success(self):
        # Run the ingest_data function
        result = asyncio.run(ingest_data())
        
        # Assertions to check that data is mapped correctly
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)  # Check that some data is returned
        self.assertTrue(all("id" in author for author in result))  # Check that each author has an ID
        self.assertTrue(all("firstName" in author for author in result))  # Check that each author has a first name
        self.assertTrue(all("lastName" in author for author in result))  # Check that each author has a last name

if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Explanation of the Code:
# 
# 1. **Fetch Data**: The `fetch_data()` function makes an asynchronous GET request to the provided API endpoint and retrieves author data.
# 2. **Ingest Data**: The `ingest_data()` function retrieves raw data using `fetch_data()` and maps it to the required entity structure. If any fields are missing, it falls back to default values.
# 3. **Unit Tests**: The test class `TestDataIngestion` includes a test method to verify that the `ingest_data()` function works correctly. It checks the output format and ensures required fields are present.
# 
# You can run the code directly, and it will execute the tests to validate the ingestion process. If you have any questions or need further modifications, feel free to ask!