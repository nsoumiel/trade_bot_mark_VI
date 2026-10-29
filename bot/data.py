"""Free daily Stooq observations. USD ETF prices converted to EUR on shared dates."""
import csv
import io
import math
from datetime import date, datetime, timezone, timedelta
from urllib.request import urlopen
from urllib.error import HTTPError
from .engine import SYMBOLS, validate
from .errors import DataError


def download(symbol):
    url = 'https://stooq.com/q/d/l/?s='+symbol+'&i=d'
    try:
        with urlopen(url, timeout=30) as response:
            body = response.read(8_000_000).decode('utf-8-sig')
    except HTTPError as exc:
        raise DataError('http_error', f'Stooq retourne HTTP {exc.code} pour {symbol}. Le téléchargement des cours de cet instrument a échoué.') from None
    text = body.lower()
    if 'api key' in text or 'apikey' in text or 'api_key' in text:
        raise DataError('provider_access', 'Stooq demande une clé ou une autorisation d’accès. Les cours gratuits sans clé ne sont pas disponibles dans cette réponse. Ne pas lancer la simulation avec des données inventées.')
    reader = csv.DictReader(io.StringIO(body))
    if not reader.fieldnames or not {'Date', 'Close'} <= set(reader.fieldnames):
        raise DataError('provider_format', 'Stooq ne renvoie pas le CSV attendu pour '+symbol+' (réponse vide, page HTML, limitation ou accès refusé).')
    records = {}
    for row in reader:
        if row.get('Date') and row.get('Close'):
            try:
                day = date.fromisoformat(row['Date'])
                price = float(row['Close'])
                if not math.isfinite(price) or price <= 0:
                    raise ValueError()
            except (ValueError, TypeError):
                raise DataError('provider_values', 'Cours ou date invalide reçu pour '+symbol) from None
            records[day.isoformat()] = price
    if not records:
        raise DataError('provider_empty', 'Aucun cours reçu pour '+symbol)
    return records


def load_remote():
    series = {s: download(s.lower()+'.us') for s in SYMBOLS}
    fx = download('eurusd')
    shared = set(fx)
    for values in series.values():
        shared &= set(values)
    # Five-year evaluation plus a full year of indicator warmup.
    today = datetime.now(timezone.utc).date()
    start = today-timedelta(days=6*366)
    rows = [dict(date=d, **{s: series[s][d]/fx[d] for s in SYMBOLS})
            for d in sorted(shared) if start.isoformat() <= d < today.isoformat() and fx[d] > 0]
    validate(rows)
    if len(rows) < 250:
        raise DataError('history_short', 'Historique commun insuffisant : '+str(len(rows))+' séances disponibles, 250 nécessaires. Vérifier SPY, IEF, GLD et EURUSD.')
    if (today-date.fromisoformat(rows[-1]['date'])).days > 5:
        raise DataError('history_stale', 'Les derniers cours communs datent du '+rows[-1]['date']+' : historique trop ancien pour actualiser le compte.')
    return rows


def load_csv(path):
    with open(path, newline='') as stream:
        rows = [dict(date=r['date'], **{s: float(r[s]) for s in SYMBOLS})
                for r in csv.DictReader(stream)]
    validate(rows)
    if len(rows) < 201:
        raise ValueError('Au moins 201 observations nécessaires')
    return rows
