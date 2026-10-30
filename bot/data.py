"""Alpaca daily IEX bars in USD, converted using ECB reference USD per EUR."""
import csv
import json
import math
import os
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError
from .engine import SYMBOLS, validate
from .errors import DataError


def request(url, label, headers=None):
    try:
        with urlopen(Request(url, headers=headers or {}), timeout=30) as response:
            body = response.read(16_000_001)
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise DataError('provider_access', f'{label} : accès refusé HTTP {exc.code}. Vérifier les clés, les droits de données et la politique réseau.') from None
        raise DataError('http_error', f'{label} retourne HTTP {exc.code}. Réessayer plus tard et vérifier le service.') from None
    if len(body) > 16_000_000:
        raise DataError('provider_format', f'{label} : réponse trop volumineuse.')
    return body


def download(symbol):
    if symbol not in SYMBOLS:
        raise DataError('provider_values', 'Symbole Alpaca non pris en charge.')
    key, secret = os.getenv('APCA_API_KEY_ID'), os.getenv('APCA_API_SECRET_KEY')
    if not key or not secret:
        raise DataError('credentials_missing', 'Renseigner APCA_API_KEY_ID et APCA_API_SECRET_KEY dans .env puis recréer le conteneur.')
    headers = {'APCA-API-KEY-ID': key, 'APCA-API-SECRET-KEY': secret}
    today = datetime.now(timezone.utc).date()
    params = dict(timeframe='1Day', start=(today-timedelta(days=6*366)).isoformat(),
                  end=today.isoformat(), limit=10000, adjustment='split', feed='iex', sort='asc')
    records, seen = {}, set()
    while True:
        body = request('https://data.alpaca.markets/v2/stocks/'+symbol+'/bars?'+urlencode(params), 'Alpaca '+symbol, headers)
        try:
            payload = json.loads(body)
            bars = payload['bars']
            if not isinstance(bars, list):
                raise ValueError()
            for bar in bars:
                stamp = datetime.fromisoformat(bar['t'].replace('Z', '+00:00'))
                if stamp.tzinfo is None:
                    raise ValueError()
                day, price = stamp.date().isoformat(), float(bar['c'])
                if not math.isfinite(price) or price <= 0:
                    raise ValueError()
                records[day] = price
            token = payload.get('next_page_token')
            if token is not None and not isinstance(token, str):
                raise ValueError()
        except (ValueError, TypeError, KeyError, AttributeError, UnicodeError):
            raise DataError('provider_format', 'Alpaca '+symbol+' : réponse JSON ou cours invalides.') from None
        if not token:
            break
        if token in seen or len(seen) >= 100:
            raise DataError('provider_format', 'Alpaca : pagination invalide.')
        seen.add(token)
        params['page_token'] = token
    if not records:
        raise DataError('provider_empty', 'Alpaca : aucun cours reçu pour '+symbol+'. Vérifier les droits IEX.')
    return records


def download_fx():
    body = request('https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml', 'BCE EUR/USD')
    records = {}
    try:
        root = ET.fromstring(body)
        for node in root.iter():
            if 'time' not in node.attrib:
                continue
            day = date.fromisoformat(node.attrib['time']).isoformat()
            for child in node:
                if child.get('currency') == 'USD':
                    price = float(child.attrib['rate'])
                    if not math.isfinite(price) or price <= 0:
                        raise ValueError()
                    records[day] = price
    except (ET.ParseError, ValueError, KeyError):
        raise DataError('provider_format', 'BCE : historique EUR/USD invalide.') from None
    if not records:
        raise DataError('provider_empty', 'BCE : aucun taux EUR/USD reçu.')
    return records


def load_remote():
    series = {s: download(s) for s in SYMBOLS}
    fx = download_fx()
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
