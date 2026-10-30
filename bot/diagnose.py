"""Safe NAS diagnostics: python -m bot.diagnose (no Telegram message or paper order)."""
import json
import os
from pathlib import Path
import tempfile
from datetime import datetime, timezone
from .data import download, download_fx, load_remote
from .errors import diagnostic


def main():
    failed = False
    print('Heure UTC du conteneur :', datetime.now(timezone.utc).isoformat())
    folder = Path(os.getenv('DATA_DIR', '/data'))
    steps = [('stockage /data', lambda: check_storage(folder))]
    steps += [(symbol, lambda s=symbol: len(download(s)))
              for symbol in ('SPY', 'IEF', 'GLD')]
    steps += [('BCE EUR/USD', lambda: len(download_fx()))]
    steps += [('historique commun en EUR', lambda: len(load_remote()))]
    for name, check in steps:
        try:
            print(name, ': OK —', check())
        except Exception as exc:
            failed = True
            print(name, ': ÉCHEC —', json.dumps(diagnostic(exc), ensure_ascii=False))
    return int(failed)


def check_storage(folder):
    with tempfile.TemporaryFile(dir=folder) as stream:
        stream.write(b'probe')
        stream.flush()
    return 'écriture autorisée'


if __name__ == '__main__':
    raise SystemExit(main())
