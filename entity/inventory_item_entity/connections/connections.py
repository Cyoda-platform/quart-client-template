# ```python
import asyncio
import logging
import aiohttp
import unittest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL = "https://api.practicesoftwaretesting.com/categories/tree"

async def fetch_data():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(API_URL, headers={"accept": "application/json"}) as response:
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
            "id": category["id"],
            "parent_id": category["parent_id"] if category["parent_id"] else 0,
            "name": category["name"],
            "slug": category["slug"],
            "sub_categories": [
                {
                    "id": sub_category["id"],
                    "parent_id": category["id"],
                    "name": sub_category["name"],
                    "slug": sub_category["slug"]
                } for sub_category in category.get("sub_categories", [])
            ]
        }
        for category in data
    ]

    return mapped_data

class TestDataIngestion(unittest.TestCase):

    def test_ingest_data_success(self):
        result = asyncio.run(ingest_data())

        # Assertions to check that data is mapped correctly
        self.assertTrue(len(result) > 0)
        self.assertEqual(result[0]["id"], "01JJSPYR8X0BZY2WJNE5R6TAA5")
        self.assertEqual(result[0]["name"], "Hand Tools")
        self.assertEqual(result[0]["slug"], "hand-tools")
        self.assertEqual(result[0]["parent_id"], 0)  # Assuming top-level categories have parent_id as 0
        self.assertTrue(len(result[0]["sub_categories"]) > 0)  # Should have sub_categories

if __name__ == "__main__":
    unittest.main()
# ``` 
# 
# ### Explanation of the Code
# 
# 1. **fetch_data()**: This asynchronous function makes a GET request to the specified API URL to retrieve category data. If the request is successful, it returns the JSON response. If there’s an error, it logs the error message.
# 
# 2. **ingest_data()**: This public function retrieves the data using `fetch_data()`. It maps the raw data structure to the required entity format. The `sub_categories` within each category are processed accordingly to maintain the parent-child relationship.
# 
# 3. **TestDataIngestion**: The unit test class uses the `unittest` framework. The `test_ingest_data_success` method runs the `ingest_data()` function and verifies that the data is mapped correctly, including checking the properties of the first category in the result.
# 
# You can run this code to fetch data from the external API and test the mapping functionality seamlessly. Let me know if you have any questions or need further adjustments! 😊