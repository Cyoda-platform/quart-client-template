# Below is a simple unit test for the `_create_post` function using the `unittest` framework. The test mocks the `entity_service.add_item` and `entity_service.get_item` methods to simulate their behavior without making actual calls to the entity service.
# 
# ### Unit Test Code
# 
# ```python
import unittest
from unittest.mock import AsyncMock, patch
import json
import asyncio
from workflow import _create_post  # Import the function to test

class TestWorkflow(unittest.IsolatedAsyncioTestCase):
    @patch('workflow.entity_service.add_item', new_callable=AsyncMock)
    @patch('workflow.entity_service.get_item', new_callable=AsyncMock)
    async def test_create_post(self, mock_get_item, mock_add_item):
        # Mock the return values for entity_service methods
        mock_add_item.return_value = "123"  # Simulate a post ID
        mock_get_item.return_value = {
            "title": "Test Post",
            "topics": ["test"],
            "body": "This is a test post.",
            "upvotes": 0,
            "downvotes": 0
        }

        # Define test data
        test_data = {
            "title": "Test Post",
            "topics": ["test"],
            "body": "This is a test post."
        }

        # Call the _create_post function
        response, status_code = await _create_post(test_data)

        # Assert the response status code
        self.assertEqual(status_code, 201)

        # Assert the response JSON
        response_data = json.loads(response)
        self.assertEqual(response_data["post_id"], "123")
        self.assertEqual(response_data["message"], "Post created successfully.")

        # Assert that the entity_service methods were called correctly
        mock_add_item.assert_called_once_with(
            token='cyoda_token',
            entity_model='post',
            entity_version='1.0',  # Replace with actual ENTITY_VERSION if different
            entity={
                "title": "Test Post",
                "topics": ["test"],
                "body": "This is a test post.",
                "upvotes": 0,
                "downvotes": 0
            }
        )
        mock_get_item.assert_called_once_with(
            token='cyoda_token',
            entity_model='post',
            entity_version='1.0',  # Replace with actual ENTITY_VERSION if different
            technical_id="123"
        )

if __name__ == '__main__':
    unittest.main()
# ```
# 
# ### Explanation of the Test
# 
# 1. **Mocking `entity_service` Methods**:
#    - The `entity_service.add_item` and `entity_service.get_item` methods are mocked using `unittest.mock.AsyncMock`. This allows us to simulate their behavior without making actual calls to the entity service.
# 
# 2. **Test Data**:
#    - A sample `test_data` dictionary is created to simulate the input data for the `_create_post` function.
# 
# 3. **Calling the Function**:
#    - The `_create_post` function is called with the test data, and the response and status code are captured.
# 
# 4. **Assertions**:
#    - The status code is asserted to be `201` (Created).
#    - The response JSON is parsed and checked to ensure it contains the correct `post_id` and `message`.
#    - The mocked `entity_service` methods are verified to have been called with the correct arguments.
# 
# 5. **Running the Test**:
#    - The test can be executed using the `unittest` framework. If the assertions pass, the test is successful.
# 
# ### Running the Test
# Save the test code in a file (e.g., `test_workflow.py`) and run it using the following command:
# 
# ```bash
# python -m unittest test_workflow.py
# ```
# 
# This test ensures that the `_create_post` function behaves as expected when creating a new post. You can expand this approach to write tests for other functions (`_add_comment`, `_upload_image`, etc.) in the workflow.