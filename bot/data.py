"""Free daily Stooq observations. USD ETF prices converted to EUR on shared dates."""
import csv
import io
from datetime import date, datetime, timezone, timedelta
from urllib.request import urlopen
from .engine import SYMBOLS, validate


def download(symbol):
    url = 'https://stooq.com/q/d/l/?s='+symbol+'&i=d'
    with urlopen(url, timeout=30) as response:
        body = response.read(8_000_000).decode('utf-8-sig')
    records = {}
    for row in csv.DictReader(io.StringIO(body)):
        if row.get('Date') and row.get('Close'):
            day = date.fromisoformat(row['Date'])
            records[day.isoformat()] = float(row['Close'])
    if not records:
        raise ValueError('Aucune donnée reçue pour '+symbol)
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
        raise ValueError('Historique insuffisant')
    if (today-date.fromisoformat(rows[-1]['date'])).days > 5:
        raise ValueError('Données trop anciennes : simulation non actualisée')
    return rows


def load_csv(path):
    with open(path, newline='') as stream:
        rows = [dict(date=r['date'], **{s: float(r[s]) for s in SYMBOLS})
                for r in csv.DictReader(stream)]
    validate(rows)
    if len(rows) < 201:
        raise ValueError('Au moins 201 observations nécessaires')
    return rows
