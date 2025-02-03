import asyncio
import logging
import aiohttp
from app_init.app_init import entity_service
import unittest
from unittest.mock import patch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL_POSTS = "https://jsonplaceholder.typicode.com/posts"
API_URL_COMMENTS = "https://jsonplaceholder.typicode.com/posts/1/comments"

async def fetch_posts_processor(meta, data):
    logger.info("Fetching posts from API.")
    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL_POSTS) as response:
            if response.status == 200:
                posts_data = await response.json()
                # Save data to post_entity
                post_entity_id = await entity_service.add_item(meta["token"], "post_entity", "v1", posts_data)
                logger.info(f"Posts data saved with ID: {post_entity_id}")
                return {"post_entity_id": post_entity_id, "records": posts_data}
            else:
                logger.error(f"Error fetching posts: {response.status}")
                raise Exception("Failed to fetch posts.")

async def fetch_comments_processor(meta, data):
    logger.info("Fetching comments from API.")
    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL_COMMENTS) as response:
            if response.status == 200:
                comments_data = await response.json()
                # Save data to comment_entity
                comment_entity_id = await entity_service.add_item(meta["token"], "comment_entity", "v1", comments_data)
                logger.info(f"Comments data saved with ID: {comment_entity_id}")
                return {"comment_entity_id": comment_entity_id, "records": comments_data}
            else:
                logger.error(f"Error fetching comments: {response.status}")
                raise Exception("Failed to fetch comments.")

async def combine_data_processor(meta, data):
    logger.info("Combining posts and comments.")
    posts = data["post_entity"]["records"]
    comments = data["comment_entity"]["records"]
    combined_data = []

    for post in posts:
        post_comments = [comment for comment in comments if comment["postId"] == post["id"]]
        combined_data.append({
            "postId": post["id"],
            "title": post["title"],
            "comments": post_comments
        })
    
    # Save combined data to combined_entity
    combined_entity_id = await entity_service.add_item(meta["token"], "combined_entity", "v1", combined_data)
    logger.info(f"Combined data saved with ID: {combined_entity_id}")
    return {"combined_entity_id": combined_entity_id, "records": combined_data}

async def generate_report_processor(meta, data):
    logger.info("Generating report from combined data.")
    combined_data = data["combined_entity"]["records"]
    
    report_data = {
        "reportId": "report_001",
        "generatedAt": "2023-10-01T12:00:00Z",
        "reportTitle": "Monthly Engagement Report",
        "totalPosts": len(combined_data),
        "totalComments": sum(len(post["comments"]) for post in combined_data),
        "postDetails": combined_data
    }
    
    # Save report data to report_entity
    report_entity_id = await entity_service.add_item(meta["token"], "report_entity", "v1", report_data)
    logger.info(f"Report data saved with ID: {report_entity_id}")
    return {"report_entity_id": report_entity_id, "report": report_data}

# Test Cases
class TestDataIngestionJob(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    @patch("aiohttp.ClientSession.get")
    @patch("app_init.app_init.entity_service.add_item")
    def test_fetch_posts_processor(self, mock_add_item, mock_get):
        # Mock the API response
        mock_response = asyncio.Future(loop=self.loop)
        mock_response.set_result([
            {"userId": 1, "id": 1, "title": "Post 1", "body": "Content of Post 1"},
            {"userId": 1, "id": 2, "title": "Post 2", "body": "Content of Post 2"},
        ])
        mock_get.return_value.__aenter__.return_value.status = 200
        mock_get.return_value.__aenter__.return_value.json = lambda: mock_response
        mock_add_item.return_value = "post_entity_id"

        meta = {"token": "test_token"}
        data = {}
        result = self.loop.run_until_complete(fetch_posts_processor(meta, data))

        mock_add_item.assert_called_once()
        self.assertEqual(result["post_entity_id"], "post_entity_id")

    @patch("aiohttp.ClientSession.get")
    @patch("app_init.app_init.entity_service.add_item")
    def test_fetch_comments_processor(self, mock_add_item, mock_get):
        # Mock the API response
        mock_response = asyncio.Future(loop=self.loop)
        mock_response.set_result([
            {"postId": 1, "id": 1, "name": "Comment 1", "email": "example1@example.com", "body": "Content of Comment 1"},
            {"postId": 1, "id": 2, "name": "Comment 2", "email": "example2@example.com", "body": "Content of Comment 2"},
        ])
        mock_get.return_value.__aenter__.return_value.status = 200
        mock_get.return_value.__aenter__.return_value.json = lambda: mock_response
        mock_add_item.return_value = "comment_entity_id"

        meta = {"token": "test_token"}
        data = {}
        result = self.loop.run_until_complete(fetch_comments_processor(meta, data))

        mock_add_item.assert_called_once()
        self.assertEqual(result["comment_entity_id"], "comment_entity_id")

    @patch("app_init.app_init.entity_service.add_item")
    def test_combine_data_processor(self, mock_add_item):
        mock_add_item.return_value = "combined_entity_id"
        meta = {"token": "test_token"}
        data = {
            "post_entity": {"records": [{"id": 1, "title": "Post 1"}, {"id": 2, "title": "Post 2"}]},
            "comment_entity": {"records": [{"postId": 1, "id": 1, "name": "Comment 1", "email": "example1@example.com", "body": "Content of Comment 1"}]}
        }

        result = self.loop.run_until_complete(combine_data_processor(meta, data))

        mock_add_item.assert_called_once()
        self.assertEqual(result["combined_entity_id"], "combined_entity_id")

    @patch("app_init.app_init.entity_service.add_item")
    def test_generate_report_processor(self, mock_add_item):
        mock_add_item.return_value = "report_entity_id"
        meta = {"token": "test_token"}
        data = {
            "combined_entity": {
                "records": [
                    {"postId": 1, "title": "Post 1", "comments": []},
                    {"postId": 2, "title": "Post 2", "comments": []}
                ]
            }
        }

        result = self.loop.run_until_complete(generate_report_processor(meta, data))

        mock_add_item.assert_called_once()
        self.assertEqual(result["report_entity_id"], "report_entity_id")

if __name__ == "__main__":
    unittest.main()