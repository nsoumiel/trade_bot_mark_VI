import io
import ssl
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from bot import app
from bot.data import download
from bot.errors import DataError, diagnostic


class DiagnosticTest(unittest.TestCase):
    def test_html_and_api_key_not_accepted_as_prices(self):
        for body, code in [(b'<html>denied</html>', 'provider_format'),
                           (b'Please provide your API key', 'provider_access'),
                           (b'Date,Close\n2026-01-01,nan\n', 'provider_values')]:
            with patch('bot.data.urlopen', return_value=io.BytesIO(body)):
                with self.assertRaises(DataError) as raised: download('spy.us')
            self.assertEqual(raised.exception.code, code)

    def test_csv_parses(self):
        with patch('bot.data.urlopen', return_value=io.BytesIO(b'Date,Close\n2026-01-01,100\n')):
            self.assertEqual(download('spy.us'), {'2026-01-01': 100.})

    def test_errors_never_publish_exception_secrets(self):
        for exc in [HTTPError('https://secret-token', 403, 'secret-token', {}, None),
                    URLError('secret-token'), RuntimeError('secret-token'),
                    PermissionError('secret-token')]:
            self.assertNotIn('secret-token', str(diagnostic(exc)))
        self.assertEqual(diagnostic(URLError(ssl.SSLError()))['code'], 'tls_error')

    def test_failed_update_retains_report_and_retries(self):
        with patch.dict(app.STATE, {'paper': {'sentinel': True}}, clear=True), patch.object(app, 'update', side_effect=PermissionError('private-path')):
            delay = app.attempt_update()
            self.assertEqual(delay, 300)
            self.assertEqual(app.STATE['paper'], {'sentinel': True})
            self.assertEqual(app.STATE['error']['code'], 'storage_permission')
            self.assertTrue(app.STATE['next_retry'])
            self.assertNotIn('private-path', str(app.STATE))
