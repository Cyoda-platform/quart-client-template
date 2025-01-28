# ```python
import asyncio
import logging
import aiohttp
import unittest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL = "https://petstore.swagger.io/v2/pet/findByStatus?status="

async def fetch_data(status: str):
    url = f"{API_URL}{status}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers={"accept": "application/json"}) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Error fetching data: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Exception occurred: {str(e)}")
            return None

async def ingest_data(status: str) -> list:
    data = await fetch_data(status)
    if data is None:
        logger.error("No data received for ingestion.")
        return []

    # Map raw data to the required entity structure
    mapped_data = [
        {
            "pet_id": pet.get("id", 0),
            "category": {
                "category_id": pet.get("category", {}).get("id", 0),
                "category_name": pet.get("category", {}).get("name", "string"),
            },
            "pet_name": pet.get("name", "string"),
            "photoUrls": pet.get("photoUrls", ["string"]),
            "tags": [
                {"id": tag.get("id", 0), "name": tag.get("name", "string")} for tag in pet.get("tags", [])
            ],
            "status": pet.get("status", "available")
        }
        for pet in data
    ]

    return mapped_data

class TestDataIngestion(unittest.TestCase):

    def test_ingest_data_available(self):
        result = asyncio.run(ingest_data("available"))
        self.assertTrue(len(result) > 0)
        self.assertEqual(result[0]["status"], "available")

    def test_ingest_data_pending(self):
        result = asyncio.run(ingest_data("pending"))
        self.assertTrue(len(result) > 0)
        self.assertEqual(result[0]["status"], "pending")

    def test_ingest_data_sold(self):
        result = asyncio.run(ingest_data("sold"))
        self.assertTrue(len(result) > 0)
        self.assertEqual(result[0]["status"], "sold")

if __name__ == "__main__":
    unittest.main()
# ``` 
# 
# This code fetches pet data from the specified external data source using the provided status parameters (available, pending, sold), maps the raw data to the defined entity structure, and provides unittests for each status to ensure functionality.