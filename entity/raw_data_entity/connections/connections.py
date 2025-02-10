# ```python
import asyncio
import logging
import aiohttp
import unittest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name())

API_URL = "https://automationexercise.com/api/productsList"

async def fetch_data():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(API_URL) as response:
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
    if data and data.get("responseCode") == 200:
        mapped_data = [
            {
                "id": product["id"],
                "name": product["name"],
                "price": product["price"],
                "brand": product["brand"],
                "category": product["category"]["category"]
            }
            for product in data["products"]
        ]
        return mapped_data
    return []

class TestDataIngestion(unittest.TestCase):

    def test_ingest_data_success(self):
        result = asyncio.run(ingest_data())
        self.assertTrue(len(result) > 0)
        self.assertEqual(result[0]["id"], 1)
        self.assertEqual(result[0]["name"], "Blue Top")
        self.assertEqual(result[0]["price"], "Rs. 500")

if __name__ == "__main__":
    unittest.main()
# ```