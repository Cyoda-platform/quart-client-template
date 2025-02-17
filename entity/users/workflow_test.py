# To write unit tests for the provided code, we can use the `unittest` framework along with `unittest.mock` to mock the `entity_service` methods. Below is an example of a simple unit test for the `_create_user` route. This test ensures that the route correctly calls the `entity_service.create_user` method and returns the expected response.
# 
# ### Unit Test Code
# 
# ```python
import unittest
from unittest.mock import AsyncMock, patch
from quart.testing import QuartClient
from workflow import app  # Import the Quart app from your module

class TestWorkflow(unittest.IsolatedAsyncioTestCase):
    async def test_create_user(self):
        # Mock the entity_service.create_user method
        with patch('workflow.entity_service.create_user', new_callable=AsyncMock) as mock_create_user:
            # Set up the test client
            test_client = QuartClient(app)

            # Define the test data
            test_data = {
                "username": "testuser",
                "password": "testpassword"
            }

            # Make a POST request to the /users/create endpoint
            response = await test_client.post('/users/create', json=test_data)

            # Assert that the response status code is 201 (Created)
            self.assertEqual(response.status_code, 201)

            # Assert that the response JSON matches the expected message
            response_data = await response.get_json()
            self.assertEqual(response_data, {"message": "User created successfully."})

            # Assert that the entity_service.create_user method was called with the correct arguments
            mock_create_user.assert_called_once_with("testuser", "testpassword")

if __name__ == '__main__':
    unittest.main()
# ```
# 
# ### Explanation of the Test
# 
# 1. **Mocking `entity_service.create_user`**:
#    - We use `unittest.mock.patch` to mock the `entity_service.create_user` method. This allows us to simulate the behavior of the method without actually calling it.
# 
# 2. **Test Client**:
#    - We create a test client using `QuartClient(app)` to simulate HTTP requests to the Quart app.
# 
# 3. **Test Data**:
#    - We define the test data (`username` and `password`) that will be sent in the POST request.
# 
# 4. **Making the Request**:
#    - We use the test client to make a POST request to the `/users/create` endpoint with the test data.
# 
# 5. **Assertions**:
#    - We assert that the response status code is `201` (Created).
#    - We assert that the response JSON matches the expected message: `{"message": "User created successfully."}`.
#    - We assert that the `entity_service.create_user` method was called once with the correct arguments (`"testuser"` and `"testpassword"`).
# 
# ### Running the Test
# To run the test, save the test code in a file (e.g., `test_workflow.py`) and execute it using the following command:
# 
# ```bash
# python -m unittest test_workflow.py
# ```
# 
# This test ensures that the `_create_user` route behaves as expected when a new user is created. You can expand this approach to write tests for other routes in the application.