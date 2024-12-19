import requests
import logging

BASE_URL = 'https://api.opendata.esett.com'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_balance_responsible_parties(code=None, country=None, name=None):
    endpoint = '/EXP01/BalanceResponsibleParties'
    params = {}
    if code:
        params['code'] = code
    if country:
        params['country'] = country
    if name:
        params['name'] = name
    response = requests.get(BASE_URL + endpoint, params=params)
    logger.info(f'Response from {endpoint}: {response.status_code}')  # Log response status
    return response.json()


def ingest_data(code=None, country=None, name=None):
    logger.info('Starting data ingestion...')
    data = get_balance_responsible_parties(code, country, name)
    logger.info(f'Ingested data: {data}')  # Log the ingested data
    return data


if __name__ == '__main__':
    # Example usage of ingest_data
    try:
        result = ingest_data(code='some_code', country='FI', name='some_name')
        print(result)
    except Exception as e:
        logger.error(f'An error occurred: {e}')  # Log any error

# Test cases
import unittest
from unittest.mock import patch

class TestDataIngestion(unittest.TestCase):
    @patch('requests.get')
    def test_get_balance_responsible_parties(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [{'id': 1, 'name': 'Responsible Party A', 'code': 'RP001', 'country': 'FI'}]
        response = get_balance_responsible_parties(code='some_code', country='FI', name='some_name')
        self.assertEqual(response, [{'id': 1, 'name': 'Responsible Party A', 'code': 'RP001', 'country': 'FI'}])

    @patch('requests.get')
    def test_ingest_data(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [{'id': 1, 'name': 'Responsible Party A', 'code': 'RP001', 'country': 'FI'}]
        result = ingest_data(code='some_code', country='FI', name='some_name')
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

if __name__ == '__main__':
    unittest.main()