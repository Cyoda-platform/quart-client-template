# Here’s a simple unit test for the `create_company` function using Python's `unittest` framework. The test will verify that the function correctly creates a company and increments the `company_id_counter`.
# 
# ```python
import unittest
import asyncio
from aiohttp import web
from workflow import create_company, company_cache, company_id_counter

class TestCreateCompany(unittest.TestCase):
    def setUp(self):
        # Reset the in-memory cache and counter before each test
        global company_cache, company_id_counter
        company_cache.clear()
        company_id_counter = 1

    def test_create_company_success(self):
        # Test data
        test_data = {
            'name': 'Test Company',
            'address': '123 Test St',
            'contact_number': '555-1234'
        }

        # Call the function
        result, status_code = asyncio.run(create_company(test_data))

        # Assertions
        self.assertEqual(status_code, 201)
        self.assertEqual(result['message'], 'Company created successfully')
        self.assertEqual(result['id'], 1)
        self.assertIn(1, company_cache)
        self.assertEqual(company_cache[1]['name'], 'Test Company')
        self.assertEqual(company_cache[1]['address'], '123 Test St')
        self.assertEqual(company_cache[1]['contact_number'], '555-1234')
        self.assertEqual(company_id_counter, 2)  # Counter should increment

if __name__ == '__main__':
    unittest.main()
# ```
# 
# ### Explanation of the Test
# 
# 1. **Setup**: The `setUp` method resets the `company_cache` and `company_id_counter` before each test to ensure a clean state.
# 
# 2. **Test Data**: A sample company data dictionary is created for testing.
# 
# 3. **Function Call**: The `create_company` function is called using `asyncio.run` to handle the asynchronous nature of the function.
# 
# 4. **Assertions**:
#    - The status code is checked to ensure it is `201` (Created).
#    - The response message is verified to confirm successful creation.
#    - The company ID is checked to ensure it matches the expected value (`1`).
#    - The `company_cache` is checked to ensure the company data is stored correctly.
#    - The `company_id_counter` is verified to ensure it increments correctly.
# 
# 5. **Running the Test**: The test can be executed by running the script directly.
# 
# ### Running the Test
# Save the test code in a file (e.g., `test_workflow.py`) and run it using the following command:
# 
# ```bash
# python -m unittest test_workflow.py
# ```
# 
# This will execute the test and verify that the `create_company` function works as expected.