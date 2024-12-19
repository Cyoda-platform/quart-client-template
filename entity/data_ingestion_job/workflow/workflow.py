import requests
from unittest import mock
import unittest

BASE_URL = 'https://api.opendata.esett.com'


def get_balance_responsible_parties(code=None, country=None, name=None):
    params = {}
    if code:
        params['code'] = code
    if country:
        params['country'] = country
    if name:
        params['name'] = name
    response = requests.get(f'{BASE_URL}/EXP01/BalanceResponsibleParties', params=params)
    return response.json() if response.status_code == 200 else response.text


def ingest_raw_data(code=None, country=None, name=None):
    data = get_balance_responsible_parties(code, country, name)
    if isinstance(data, dict) and 'error' in data:
        raise Exception('Error fetching data')
    return data


def log_process(job_id, status, message):
    log_entry = {
        'job_id': job_id,
        'status': status,
        'message': message
    }
    # Log the entry to a logging system (mocked here)
    print('Log Entry:', log_entry)
    return log_entry


def notify stakeholders(job_id):
    notification_entry = {
        'job_id': job_id,
        'message': 'Data ingestion completed successfully!'
    }
    # Send notification logic (mocked here)
    print('Notification Sent:', notification_entry)
    return notification_entry


class TestIngestionFunctions(unittest.TestCase):
    @mock.patch('requests.get')
    def test_get_balance_responsible_parties_success(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'data': 'example_data'}

        result = get_balance_responsible_parties(code='BRP123', country='FI', name='Example BRP')
        self.assertEqual(result, {'data': 'example_data'})

    @mock.patch('requests.get')
    def test_get_balance_responsible_parties_failure(self, mock_get):
        mock_get.return_value.status_code = 404

        result = get_balance_responsible_parties(code='BRP123', country='FI', name='Example BRP')
        self.assertEqual(result, '404 Not Found')

    @mock.patch('builtins.print')  # Mock print to test logging
    def test_log_process(self, mock_print):
        job_id = 'job_001'
        status = 'completed'
        message = 'Data ingestion completed.'

        log_entry = log_process(job_id, status, message)
        mock_print.assert_called_with('Log Entry:', {'job_id': 'job_001', 'status': 'completed', 'message': 'Data ingestion completed.'})

    @mock.patch('builtins.print')  # Mock print to test notification
    def test_notify_stakeholders(self, mock_print):
        job_id = 'job_001'

        notification_entry = notify_stakeholders(job_id)
        mock_print.assert_called_with('Notification Sent:', {'job_id': 'job_001', 'message': 'Data ingestion completed successfully!'})


if __name__ == '__main__':
    unittest.main()