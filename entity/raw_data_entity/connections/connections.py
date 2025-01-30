# Here's the Python code to fetch data from the specified external data source (the Authors API). This code includes the `ingest_data` function that processes the fetched data and maps it to the required entity structure. It also includes unit tests for the function.
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
            "id": author["id"],
            "idBook": author["idBook"],
            "firstName": author["firstName"],
            "lastName": author["lastName"]
        } for author in data
    ]

    return mapped_data

# Unit Tests
class TestDataIngestion(unittest.TestCase):
    def test_ingest_data_success(self):
        # Run the ingest_data function and fetch results
        result = asyncio.run(ingest_data())
        
        # Check that data is processed correctly
        self.assertTrue(len(result) > 0)
        self.assertEqual(result[0]["id"], 1)
        self.assertEqual(result[0]["firstName"], "First Name 1")
        self.assertEqual(result[1]["lastName"], "Last Name 2")

if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Explanation:
# 1. **`fetch_data()` Function**:
#    - This function makes an asynchronous GET request to the specified API URL and returns the JSON response if the request is successful.
# 
# 2. **`ingest_data()` Function**:
#    - This function calls `fetch_data()` to retrieve the data.
#    - It maps the retrieved data to a defined entity structure, which matches the provided entity format.
# 
# 3. **Unit Tests**:
#    - The `TestDataIngestion` class uses the `unittest` framework to test the `ingest_data()` function.
#    - The `test_ingest_data_success` method runs the ingestion function and checks whether the data returned is processed and structured correctly.
# 
# You can run this code to fetch the author data and validate the functionality right away! If you need any more adjustments or details, feel free to ask! 😊