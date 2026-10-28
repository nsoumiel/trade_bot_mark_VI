import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bot import app
from test_engine import prices


class PersistenceTest(unittest.TestCase):
    def test_restart_and_no_duplicate_trades(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(app, 'DATA', Path(directory)), patch.object(app, 'notify') as notify, patch.dict('os.environ', {'TAX_RATE': '.30', 'RISK_STOP': '.15'}):
            with patch.object(app, 'load_remote', return_value=prices(300)):
                app.update()
                first = json.loads((Path(directory)/'account.json').read_text())
                self.assertEqual(first['report']['observations'], 1)
                self.assertEqual(notify.call_count, 1)
                app.update()
                self.assertEqual(notify.call_count, 1)
                self.assertEqual(first, json.loads((Path(directory)/'account.json').read_text()))
            with patch.object(app, 'load_remote', return_value=prices(301)):
                app.update()
                account = json.loads((Path(directory)/'account.json').read_text())
                self.assertEqual(account['report']['observations'], 2)
                self.assertEqual(account['rows'][:-1], first['rows'])
                self.assertEqual(notify.call_count, 1)

    def test_config_change_refused(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(app, 'DATA', Path(directory)), patch.object(app, 'notify'), patch.object(app, 'load_remote', return_value=prices(300)), patch.dict('os.environ', {'TAX_RATE': '.30', 'RISK_STOP': '.15'}):
            app.update()
            with patch.dict('os.environ', {'TAX_RATE': '.31'}):
                with self.assertRaises(ValueError): app.update()
