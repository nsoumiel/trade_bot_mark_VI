import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from bot.data import download, download_fx, load_remote
from bot.errors import DataError, diagnostic


class AlpacaTest(unittest.TestCase):
    def setUp(self):
        self.credentials = patch.dict('os.environ', {'APCA_API_KEY_ID': 'test-key', 'APCA_API_SECRET_KEY': 'test-secret'})
        self.credentials.start()
        self.addCleanup(self.credentials.stop)

    def response(self, bars, token=None):
        return io.BytesIO(json.dumps({'bars': bars, 'next_page_token': token}).encode())

    def test_authentication_pagination_and_feed(self):
        with patch('bot.data.urlopen', side_effect=[self.response([{'t': '2026-01-02T05:00:00Z', 'c': 100}], 'next'), self.response([{'t': '2026-01-05T05:00:00Z', 'c': 101}])]) as http:
            self.assertEqual(download('SPY'), {'2026-01-02': 100, '2026-01-05': 101})
        first, second = [c.args[0] for c in http.call_args_list]
        self.assertIn('feed=iex', first.full_url)
        self.assertIn('adjustment=split', first.full_url)
        self.assertEqual(first.get_header('Apca-api-key-id'), 'test-key')
        self.assertEqual(first.get_header('Apca-api-secret-key'), 'test-secret')
        self.assertIn('page_token=next', second.full_url)

    def test_credentials_missing_without_network(self):
        with patch.dict('os.environ', {}, clear=True), patch('bot.data.urlopen') as http:
            with self.assertRaises(DataError) as e: download('SPY')
            self.assertEqual(e.exception.code, 'credentials_missing')
            http.assert_not_called()

    def test_access_errors_do_not_leak_secrets(self):
        for status in (401, 403, 429, 500):
            with patch('bot.data.urlopen', side_effect=HTTPError('https://secret', status, 'test-secret', {}, None)):
                with self.assertRaises(DataError) as e: download('SPY')
            message = str(diagnostic(e.exception))
            self.assertIn(str(status), message)
            self.assertIn('SPY', message)
            self.assertNotIn('test-secret', message)

    def test_invalid_and_empty_responses(self):
        for body in [b'<html>denied</html>', b'{}', b'{"bars":null}', b'{"bars":[]}', b'{"bars":[{"t":"2026-01-02T05:00:00Z","c":0}]}']:
            with patch('bot.data.urlopen', return_value=io.BytesIO(body)):
                with self.assertRaises(DataError): download('SPY')

    def test_repeated_page_token_rejected(self):
        with patch('bot.data.urlopen', side_effect=[self.response([], 'same'), self.response([], 'same')]):
            with self.assertRaises(DataError): download('SPY')

    def test_ecb_rates_and_invalid_response(self):
        xml = b'<Envelope xmlns="urn:ecb"><Cube><Cube time="2026-01-02"><Cube currency="USD" rate="1.25"/></Cube></Cube></Envelope>'
        with patch('bot.data.urlopen', return_value=io.BytesIO(xml)) as http:
            self.assertEqual(download_fx(), {'2026-01-02': 1.25})
            self.assertNotIn('Apca-api-key-id', dict(http.call_args.args[0].header_items()))
        for body in [b'<html/>', b'invalid', xml.replace(b'1.25', b'nan')]:
            with patch('bot.data.urlopen', return_value=io.BytesIO(body)):
                with self.assertRaises(DataError): download_fx()

    def test_eur_conversion_and_current_day_exclusion(self):
        from datetime import datetime, timezone, timedelta
        today = datetime.now(timezone.utc).date()
        days = [(today-timedelta(days=i)).isoformat() for i in range(301)]
        with patch('bot.data.download', return_value=dict.fromkeys(days, 100.)), patch('bot.data.download_fx', return_value=dict.fromkeys(days, 1.25)):
            rows = load_remote()
        self.assertEqual(len(rows), 300)
        self.assertEqual(rows[-1]['SPY'], 80.)
        self.assertLess(rows[-1]['date'], today.isoformat())
