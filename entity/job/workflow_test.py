# workflow_test.py
import asyncio
import unittest
from unittest.mock import patch, AsyncMock

from quart import Quart

# Import functions and variables from the module under test.
from workflow import (
    create_report,
    _fetch_bitcoin_rates,
    _send_email,
    cyoda_token,
    ENTITY_VERSION,
    logger,
)

# --- Custom Fake Classes for aiohttp ---
class FakeResponse:
    async def json(self):
        return {'bitcoin': {'usd': 50000, 'eur': 45000}}

class FakeRequestContextManager:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self.response

    async def __aexit__(self, exc_type, exc, tb):
        pass

class FakeClientSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    def get(self, url):
        expected_url = 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd,eur'
        assert url == expected_url, f"Unexpected URL: {url}"
        return FakeRequestContextManager(FakeResponse())

# --- Test Cases ---

class TestFetchBitcoinRates(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_bitcoin_rates(self):
        """Test that _fetch_bitcoin_rates returns the expected rate data."""
        with patch('workflow.aiohttp.ClientSession', return_value=FakeClientSession()):
            rates = await _fetch_bitcoin_rates()
            expected = {"btc_usd": 50000, "btc_eur": 45000}
            self.assertEqual(rates, expected)

class TestCreateReport(unittest.IsolatedAsyncioTestCase):
    async def test_create_report_success(self):
        """Test that create_report processes data correctly and returns a proper response."""
        test_email = "test@example.com"
        test_data = {"email": test_email}

        # Create a minimal Quart app to push an app context
        app = Quart(__name__)
        async with app.app_context():
            with patch('workflow.aiohttp.ClientSession', return_value=FakeClientSession()):
                with patch('app_init.app_init.entity_service.add_item', new=AsyncMock(return_value="report123")) as add_item_mock:
                    with patch('asyncio.create_task') as create_task_mock:
                        # Patch jsonify to simply return its input (a dict) rather than a Response.
                        with patch('workflow.jsonify', side_effect=lambda data: data):
                            response, status = await create_report(test_data)

                            expected_response = {"report_id": "report123", "status": "Report is being generated."}
                            self.assertEqual(response, expected_response)
                            self.assertEqual(status, 202)

                            expected_report_data = {
                                "btc_usd_rate": 50000,
                                "btc_eur_rate": 45000,
                                "timestamp": "2023-10-01T12:00:00Z"
                            }
                            add_item_mock.assert_awaited_once_with(cyoda_token, 'report', ENTITY_VERSION, expected_report_data)

                            create_task_mock.assert_called_once()
                            scheduled_coro = create_task_mock.call_args[0][0]
                            self.assertTrue(asyncio.iscoroutine(scheduled_coro))

class TestSendEmail(unittest.IsolatedAsyncioTestCase):
    async def test_send_email_logs_info(self):
        """Test that _send_email logs the 'Sending email' message."""
        with patch.object(logger, 'info') as mock_logger_info:
            await _send_email("report123", {"btc_usd": 50000, "btc_eur": 45000}, "test@example.com")
            mock_logger_info.assert_called_with("Sending email")

# --- Run the tests ---
if __name__ == '__main__':
    unittest.main()
