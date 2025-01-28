# ```python
import asyncio
import logging
import aiohttp
import unittest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL = "https://petstore3.swagger.io/api/v3/pet"

async def fetch_data(pet_id):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_URL}/{pet_id}", headers={"accept": "application/xml"}) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.error(f"Error fetching data: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Exception occurred: {str(e)}")
            return None

async def ingest_data(pet_id) -> dict:
    raw_data = await fetch_data(pet_id)
    if raw_data is None:
        logger.error("No data received for ingestion.")
        return {}

    # Assuming we need to parse the XML response
    import xml.etree.ElementTree as ET
    root = ET.fromstring(raw_data)

    # Map the raw data to our entity structure
    mapped_data = {
        "id": root.find('id').text,
        "name": root.find('name').text,
        "category": {
            "id": root.find('category/id').text,
            "name": root.find('category/name').text
        },
        "photoUrls": [photo.text for photo in root.findall('photoUrls/photoUrl')],
        "tags": [
            {
                "id": tag.find('id').text,
                "name": tag.find('name').text
            }
            for tag in root.findall('tags/tag')
        ],
        "status": root.find('status').text
    }

    return mapped_data

class TestDataIngestion(unittest.TestCase):

    def test_ingest_data_success(self):
        result = asyncio.run(ingest_data("7517577846774566682"))

        self.assertTrue("id" in result)
        self.assertEqual(result["id"], "7517577846774566682")
        self.assertEqual(result["name"], "G5q#z:_jJRWm6Vm.g`v1xMri0cBv[V]#GCcM")
        self.assertEqual(result["category"]["id"], "4328014582300286193")
        self.assertEqual(result["status"], "sold")
        self.assertTrue(len(result["photoUrls"]) > 0)
        self.assertTrue(len(result["tags"]) > 0)

if __name__ == "__main__":
    unittest.main()
# ```