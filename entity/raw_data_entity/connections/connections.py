# ```python
import asyncio
import logging
import aiohttp
import unittest
from unittest.mock import patch
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL = "https://fakerestapi.azurewebsites.net/api/v1/Activities"

async def fetch_data() -> List[dict]:
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

async def ingest_data() -> List[dict]:
    data = await fetch_data()
    if data is None:
        logger.error("No data received for ingestion.")
        return []

    # Map raw data to the entity structure
    mapped_data = [
        {
            "id": activity["id"],
            "title": activity["title"],
            "due_date": activity["dueDate"],
            "completed": activity["completed"]
        }
        for activity in data
    ]

    return mapped_data

class TestDataIngestion(unittest.TestCase):

    def test_ingest_data_success(self):
        result = asyncio.run(ingest_data())

        # Assertions to check that data is mapped correctly
        self.assertTrue(len(result) > 0)
        self.assertEqual(result[0]["id"], 1)
        self.assertEqual(result[0]["title"], "Activity 1")
        self.assertEqual(result[0]["due_date"], "2025-01-22T21:36:27.6587562+00:00")
        self.assertEqual(result[0]["completed"], False)

if __name__ == "__main__":
    unittest.main()
# ```