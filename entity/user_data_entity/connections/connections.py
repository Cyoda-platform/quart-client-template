# ```python
import asyncio
import logging
import aiohttp
import unittest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_BASE_URL = "https://reqres.in/api"

async def fetch_user(user_id):
    url = f"{API_BASE_URL}/users/{user_id}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    return {"status": 404, "error": "Not Found"}
                else:
                    logger.error(f"Error fetching data: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Exception occurred: {str(e)}")
            return None

async def ingest_data(user_id) -> dict:
    raw_data = await fetch_user(user_id)
    if raw_data is None:
        logger.error("No data received for ingestion.")
        return {}
    
    # Map raw data to the expected entity structure
    if "data" in raw_data:
        mapped_data = {
            "id": raw_data["data"]["id"],
            "email": raw_data["data"]["email"],
            "first_name": raw_data["data"]["first_name"],
            "last_name": raw_data["data"]["last_name"],
            "avatar": raw_data["data"]["avatar"]
        }
    else:
        mapped_data = {
            "status": raw_data.get("status", None),
            "error": raw_data.get("error", "User not found")
        }

    return mapped_data

class TestDataIngestion(unittest.TestCase):

    def test_ingest_data_success(self):
        user_id = 2  # Test with a valid user ID
        result = asyncio.run(ingest_data(user_id))

        # Assertions to check that data is mapped correctly
        self.assertEqual(result["id"], 2)
        self.assertEqual(result["email"], "janet.weaver@reqres.in")
        self.assertEqual(result["first_name"], "Janet")
        self.assertEqual(result["last_name"], "Weaver")
        self.assertEqual(result["avatar"], "https://reqres.in/img/faces/2-image.jpg")

    def test_ingest_data_not_found(self):
        user_id = 23  # Test with an invalid user ID
        result = asyncio.run(ingest_data(user_id))

        # Assertions to check that the error is correctly handled
        self.assertEqual(result["status"], 404)
        self.assertEqual(result["error"], "Not Found")

if __name__ == "__main__":
    unittest.main()
# ``` 
# 
# ### Explanation of the Code
# 
# 1. **`fetch_user(user_id)` Function**:
#    - This asynchronous function sends a GET request to the ReqRes API to retrieve user data based on the provided user ID.
#    - It handles both successful responses (HTTP 200) and cases where the user is not found (HTTP 404).
# 
# 2. **`ingest_data(user_id)` Function**:
#    - This function calls `fetch_user()` to obtain the raw data and maps it to the expected entity structure.
#    - If the raw data contains user details, it maps those fields; otherwise, it returns an error structure.
# 
# 3. **Unit Tests**:
#    - The `TestDataIngestion` class contains unit tests for both valid and invalid user IDs.
#    - The tests ensure that the mapped data is correct for valid IDs and that appropriate error messages are returned for invalid IDs.
# 
# This code can be executed in an isolated environment to test the functionality of data retrieval from the ReqRes API.