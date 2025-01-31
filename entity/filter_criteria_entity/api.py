# Here's an implementation of a `api.py` file for a Quart application that allows saving the `filter_criteria_entity`. This implementation will include the necessary APIs to handle incoming requests for saving filter criteria, along with corresponding tests that utilize mocking for external services.
# 
# ### Implementation of `api.py`
# 
# ```python
from quart import Quart, request, jsonify
import logging
from app_init.app_init import entity_service

app = Quart(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/filter_criteria', methods=['POST'])
async def save_filter_criteria():
    """API endpoint to save filter criteria entity."""
    try:
        data = await request.get_json()
        
        # Validate and process the incoming data
        if not data or 'name' not in data or 'sex' not in data:
            return jsonify({"error": "Invalid input data"}), 400
        
        token = request.headers.get('Authorization')
        entity_id = await entity_service.add_item(token, 'filter_criteria_entity', '1.0', data)
        
        return jsonify({"message": "Filter criteria saved successfully", "id": entity_id}), 201
    except Exception as e:
        logger.error(f"Error in save_filter_criteria: {e}")
        return jsonify({"error": str(e)}), 500

# Testing with Mocks
import unittest
from unittest.mock import patch

class TestFilterCriteriaAPI(unittest.TestCase):

    @patch("app_init.app_init.entity_service.add_item")
    def test_save_filter_criteria(self, mock_add_item):
        mock_add_item.return_value = "filter_criteria_id"
        
        app.testing = True
        client = app.test_client()

        response = client.post('/filter_criteria', 
                                json={"name": "Bert", "sex": "M", "minAge": 5, "maxAge": 20}, 
                                headers={"Authorization": "test_token"})
        
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['message'], "Filter criteria saved successfully")
        self.assertEqual(response.json['id'], "filter_criteria_id")
        
    def test_save_filter_criteria_invalid(self):
        app.testing = True
        client = app.test_client()

        response = client.post('/filter_criteria', 
                                json={"invalid_key": "value"}, 
                                headers={"Authorization": "test_token"})
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['error'], "Invalid input data")

    @patch("app_init.app_init.entity_service.add_item")
    def test_save_filter_criteria_exception(self, mock_add_item):
        mock_add_item.side_effect = Exception("Service error")
        
        app.testing = True
        client = app.test_client()

        response = client.post('/filter_criteria', 
                                json={"name": "Bert", "sex": "M"}, 
                                headers={"Authorization": "test_token"})
        
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json['error'], "Service error")

if __name__ == "__main__":
    unittest.main()
# ```
# 
# ### Explanation:
# 
# 1. **API Endpoint**:
#    - **`/filter_criteria`**: A POST endpoint to accept a JSON object representing the filter criteria. It validates the input before calling the `entity_service.add_item` method to save the criteria.
#    - It returns a success message with the newly created entity ID or an error message if the input is invalid or if an exception occurs.
# 
# 2. **Unit Tests**:
#    - **Mocking**: The tests use mocking to simulate the behavior of the `add_item` method so that the tests can run in isolation without affecting the actual data.
#    - Each test checks different scenarios:
#      - Successfully saving valid filter criteria.
#      - Handling invalid input data.
#      - Managing exceptions from the service layer.
# 
# Feel free to ask if you need any further modifications or additional features!