# Here’s a Python code snippet that fetches data from the external data source you specified and processes it according to the requirements. The code includes an `ingest_data` function that handles the ingestion process and returns the mapped data. Additionally, I've included simple tests to validate the functionality.
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
            "id_book": author["idBook"],
            "first_name": author["firstName"],
            "last_name": author["lastName"]
        } for author in data
    ]

    return mapped_data

class TestDataIngestion(unittest.TestCase):

    def test_ingest_data_success(self):
        # Run the ingest_data function
        result = asyncio.run(ingest_data())

        # Assertions to check that data is mapped correctly
        self.assertIsInstance(result, list)
        if len(result) > 0:
            self.assertTrue(all("id" in author for author in result))
            self.assertTrue(all("id_book" in author for author in result))
            self.assertTrue(all("first_name" in author for author in result))
            self.assertTrue(all("last_name" in author for author in result))

if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Explanation of the Code
# 
# 1. **`fetch_data()` Function**: This asynchronous function makes a GET request to the specified API URL to retrieve author data. It logs an error if the request fails or if an exception occurs.
# 
# 2. **`ingest_data()` Function**: This function retrieves the data using `fetch_data()`. If the data is successfully received, it maps the raw data to the required entity structure by renaming the fields. It returns the mapped data as a list.
# 
# 3. **Testing**: The `TestDataIngestion` class uses `unittest` to define a test for the `ingest_data()` function. It checks if the result is a list and if each author entry contains the necessary fields.
# 
# You can run the code in an isolated environment to test the `ingest_data` functionality without any mocks. Let me know if you have any questions or need further modifications! 😊