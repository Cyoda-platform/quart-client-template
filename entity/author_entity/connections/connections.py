# Here's the Python code to fetch data from the external data source specified in your request, map the response to the `author_entity`, and save it to the entity. I've also included tests with mocks for external services to allow for isolated testing.
# 
# ```python
import logging
import requests
from common.app_init import entity_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ingest_data(token):
    """Fetches author data from the external API and saves it to the author_entity."""
    url = "https://fakerestapi.azurewebsites.net/api/v1/Authors"
    headers = {
        "accept": "text/plain; v=1.0"
    }

    try:
        # Fetch data from external API
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raises an error for 4XX/5XX responses
        authors_data = response.json()

        # Map the response to the entity structure
        authors_to_save = []
        for author in authors_data:
            author_entity = {
                "id": author["id"],
                "first_name": author["firstName"],
                "last_name": author["lastName"]
            }
            authors_to_save.append(author_entity)

        # Save each author to the author_entity
        for author in authors_to_save:
            entity_service.add_item(token, "author_entity", "1.0", author)  # Assuming ENTITY_VERSION is "1.0"

        logger.info("Authors ingested and saved successfully.")

    except requests.HTTPError as e:
        logger.error(f"HTTP error occurred: {e}")
    except Exception as e:
        logger.error(f"An error occurred: {e}")

# Testing the ingest_data function
import unittest
from unittest.mock import patch, MagicMock

class TestIngestData(unittest.TestCase):

    @patch('requests.get')
    @patch('common.app_init.entity_service.add_item')
    def test_ingest_data(self, mock_add_item, mock_get):
        # Arrange
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "id": 1,
                "idBook": 1,
                "firstName": "First Name 1",
                "lastName": "Last Name 1"
            },
            {
                "id": 2,
                "idBook": 1,
                "firstName": "First Name 2",
                "lastName": "Last Name 2"
            }
        ]
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        test_token = "test_token"

        # Act
        ingest_data(test_token)

        # Assert
        self.assertEqual(mock_add_item.call_count, 2)  # Ensure two authors are saved
        mock_add_item.assert_any_call(test_token, "author_entity", "1.0", {
            "id": 1,
            "first_name": "First Name 1",
            "last_name": "Last Name 1"
        })
        mock_add_item.assert_any_call(test_token, "author_entity", "1.0", {
            "id": 2,
            "first_name": "First Name 2",
            "last_name": "Last Name 2"
        })

    @patch('requests.get')
    def test_ingest_data_http_error(self, mock_get):
        # Arrange
        mock_get.side_effect = requests.HTTPError("HTTP Error")
        test_token = "test_token"

        # Act
        ingest_data(test_token)

        # Assert
        mock_get.assert_called_once()
        
    @patch('requests.get')
    def test_ingest_data_exception(self, mock_get):
        # Arrange
        mock_get.side_effect = Exception("Some error")
        test_token = "test_token"

        # Act
        ingest_data(test_token)

        # Assert
        mock_get.assert_called_once()

if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Explanation:
# - **Function `ingest_data(token)`**: This function fetches data from the specified external API, processes it to match the structure of `author_entity`, and saves it using the `entity_service.add_item`.
# - **Mapping**: The author data returned from the API is mapped to the expected format for `author_entity`, which is structured with `id`, `first_name`, and `last_name`.
# - **Error Handling**: The function includes error handling for HTTP errors and general exceptions.
# - **Unit Tests**: The tests use the `unittest` framework with mocks to simulate the behavior of the `requests.get` function and the `entity_service.add_item` method.
# - **Testing Scenarios**: Tests check the successful ingestion of data, handling of HTTP errors, and handling of general exceptions. 
# 
# You can run the tests in the same file to validate the functionality of the `ingest_data` function.