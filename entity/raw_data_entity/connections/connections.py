# ```python
import asyncio
import logging
import aiohttp
import unittest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name())

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
    mapped_data = [{
        "id": category["id"],
        "name": category["name"],
        "slug": category["slug"],
        "parent_id": category["parent_id"],
        "sub_categories": category["sub_categories"]
    } for category in data]
    return mapped_data

class TestDataIngestion(unittest.TestCase):

    def test_ingest_data(self):
        result = asyncio.run(ingest_data())
        self.assertTrue(len(result) > 0)
        self.assertEqual(result[0]["id"], "01JKR602ZXDRRXNZ1M5Y1T4496")
        self.assertEqual(result[0]["name"], "Hand Tools")
        self.assertEqual(result[0]["slug"], "hand-tools")
        self.assertIsNone(result[0]["parent_id"])
        self.assertTrue(len(result[0]["sub_categories"]) > 0)

if __name__ == "__main__":
    unittest.main()
# ```