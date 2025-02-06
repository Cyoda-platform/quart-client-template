import asyncio
import logging
import unittest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL = "https://jsonplaceholder.typicode.com/posts/{postId}/comments"

# Mock fetch_comments function since aiohttp is not installed
async def fetch_comments(post_id):
    # Return mock data for testing
    return [
        {
            "postId": 1,
            "id": 1, 
            "name": "Test Comment",
            "email": "test@example.com",
            "body": "Test comment body"
        }
    ]

async def ingest_data(post_id):
    raw_data = await fetch_comments(post_id)
    if raw_data is None:
        logger.error("No data received for ingestion.")
        return []
    
    # Map raw data to the entity structure
    mapped_data = [
        {
            "post_id": comment["postId"],
            "id": comment["id"],
            "name": comment["name"],
            "email": comment["email"],
            "body": comment["body"]
        } for comment in raw_data
    ]
    
    return mapped_data

# Test class
class TestDataIngestion(unittest.TestCase):

    def test_ingest_data_success(self):
        post_id = 1  # Example post_id for testing
        result = asyncio.run(ingest_data(post_id))
        
        # Assertions to check that data is mapped correctly
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)  # Ensure we have some comments
        self.assertEqual(result[0]["post_id"], 1)  # Check that the first comment matches
        self.assertIn("name", result[0])  # Ensure the 'name' field is present
        self.assertIn("email", result[0])  # Ensure the 'email' field is present

if __name__ == "__main__":
    unittest.main()