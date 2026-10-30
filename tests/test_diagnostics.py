import io
import ssl
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from bot import app
from bot.data import download
from bot.errors import DataError, diagnostic


class DiagnosticTest(unittest.TestCase):
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
