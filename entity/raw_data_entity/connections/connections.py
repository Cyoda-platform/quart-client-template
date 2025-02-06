# ```python
import asyncio
import logging
import aiohttp
import unittest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL = "https://jsonplaceholder.typicode.com/users"

async def fetch_data():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(API_URL) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Error fetching data: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Exception occurred: {str(e)}")
            return []

async def ingest_data() -> list:
    data = await fetch_data()
    if not data:
        logger.warning("No data received for ingestion.")
        return []
    mapped_data = [
        {
            "id": user["id"],
            "name": user["name"],
            "username": user["username"],
            "email": user["email"],
            "address": {
                "street": user["address"]["street"],
                "suite": user["address"]["suite"],
                "city": user["address"]["city"],
                "zipcode": user["address"]["zipcode"],
                "geo": {
                    "lat": user["address"]["geo"]["lat"],
                    "lng": user["address"]["geo"]["lng"],
                },
            },
            "phone": user["phone"],
            "website": user["website"],
            "company": {
                "name": user["company"]["name"],
                "catchPhrase": user["company"]["catchPhrase"],
                "bs": user["company"]["bs"],
            },
        }
        for user in data
    ]
    return mapped_data

class TestDataIngestion(unittest.TestCase):

    def test_ingest_data(self):
        result = asyncio.run(ingest_data())
        self.assertEqual(len(result), 10)
        self.assertEqual(result[0]["id"], 1)
        self.assertEqual(result[0]["name"], "Leanne Graham")
        self.assertEqual(result[0]["email"], "Sincere@april.biz")
        self.assertEqual(result[0]["address"]["city"], "Gwenborough")
        self.assertEqual(result[0]["company"]["name"], "Romaguera-Crona")

if __name__ == "__main__":
    unittest.main()
# ```