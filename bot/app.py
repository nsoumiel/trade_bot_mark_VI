"""Local read-only dashboard and persistent daily paper account; no broker integration."""
import json
import logging
import os
from pathlib import Path
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from .data import load_remote
from .engine import Settings, simulate

DATA = Path(os.environ.get('DATA_DIR', '/data'))
LOCK = threading.Lock()
STATE = {'status': 'Démarrage — aucune donnée validée', 'paper': None, 'backtest': None}


def atomic(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, allow_nan=False), encoding='utf-8')
    tmp.replace(path)


def notify(message):
    token, chat = os.getenv('TELEGRAM_BOT_TOKEN'), os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat:
        return
    try:
        request = Request('https://api.telegram.org/bot'+token+'/sendMessage',
                          data=urlencode({'chat_id': chat, 'text': message}).encode())
        with urlopen(request, timeout=15) as response:
            if not json.load(response).get('ok'):
                logging.warning('Notification Telegram refusée')
    except Exception:
        # Never log a URL or an exception containing the bot token.
        logging.warning('Échec de notification Telegram (sans relance automatique)')


def update():
    fresh = load_remote()
    cfg = Settings(tax_rate=float(os.getenv('TAX_RATE', '.30')),
                   stop=float(os.getenv('RISK_STOP', '.15')))
    path = DATA/'account.json'
    existing = json.loads(path.read_text()) if path.exists() else None
    if existing:
        if existing['settings'] != cfg.__dict__:
            raise ValueError('Paramètres modifiés : conserver ceux du compte ou archiver data pour un nouveau compte')
        rows = existing['rows']
        # Freeze previously consumed prices. Only append later observations.
        additions = [r for r in fresh if r['date'] > rows[-1]['date']]
        rows = rows+additions
        previous_count = len(existing['report']['trades'])
    else:
        rows = fresh[-201:]
        previous_count = 0
    paper = simulate(rows, cfg)
    backtest = {'strategy': simulate(fresh, cfg), 'passive': simulate(fresh, cfg, passive=True)}
    account = dict(settings=cfg.__dict__, rows=rows, report=paper)
    atomic(path, account)
    result = dict(status='Actualisé', updated=datetime.now(timezone.utc).isoformat(),
                  last_market_date=rows[-1]['date'], paper=paper, backtest=backtest)
    atomic(DATA/'report.json', result)
    with LOCK:
        STATE.clear()
        STATE.update(result)
    new_trades = paper['trades'][previous_count:]
    if new_trades:
        notify('PAPER uniquement — '+ '; '.join(t['side']+' '+t['symbol']+' '+t['date'] for t in new_trades)
               + '\nValeur nette de liquidation estimée : '+str(paper['liquidation_net'])+' EUR')
    if paper['halted'] and not (existing and existing['report']['halted']):
        notify('PAPER : seuil de baisse atteint, compte en arrêt permanent. Revue manuelle nécessaire.')


def worker():
    while True:
        try:
            update()
        except Exception:
            logging.warning('Actualisation impossible : vérifier données, réseau ou paramètres')
            with LOCK:
                STATE['status'] = 'Actualisation échouée — données affichées potentiellement anciennes'
        time.sleep(21600)


PAGE = '''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Paper NAS</title><style>body{font:17px system-ui;max-width:1100px;margin:3em auto;padding:1em;background:#101923;color:#e7edf5}section{background:#1b2a3a;padding:1.5em;margin:1em 0;border-radius:12px}td,th{padding:.6em;text-align:left}svg{width:100%;height:180px}small{color:#c0ccda}</style>
<h1>Paper NAS · compte virtuel en euros</h1><p>Simulation uniquement · aucun ordre réel · aucun rendement garanti</p>
<section><strong id="status"></strong><p id="date"></p><p id="paper"></p><svg id="chart" viewBox="0 0 1000 180" role="img" aria-label="Évolution du compte virtuel"></svg></section>
<section><h2>Recherche historique</h2><p id="research"></p><small>Résultats exploratoires, sans validation indépendante. Distributions et leur fiscalité non modélisées : ces chiffres ne permettent pas de conclure à une rentabilité réelle.</small></section>
<section><h2>Transactions virtuelles récentes</h2><table><thead><tr><th>Date</th><th>Sens</th><th>Instrument</th><th>Montant €</th></tr></thead><tbody id="trades"></tbody></table></section>
<p>Le seuil de baisse déclenche une sortie au prochain cours disponible ; il ne plafonne pas la perte. Estimation fiscale simplifiée et configurable, à vérifier avec un professionnel.</p>
<script>
const euro=n=>new Intl.NumberFormat('fr-FR',{style:'currency',currency:'EUR'}).format(n);
async function refresh(){try{const s=await fetch('/api/status').then(r=>r.json());document.getElementById('status').textContent=s.status;document.getElementById('date').textContent='Dernière séance : '+(s.last_market_date||'en attente');
if(!s.paper)return;const p=s.paper;document.getElementById('paper').textContent='Liquidation nette estimée : '+euro(p.liquidation_net)+' · Baisse maximale observée : '+(p.max_drawdown*100).toFixed(1)+' % · '+(p.halted?'ARRÊT DU COMPTE':'Surveillance active');
const vals=p.curve.map(x=>x.net),lo=Math.min(10000,...vals),hi=Math.max(10001,...vals);let svg=document.getElementById('chart');svg.replaceChildren();const line=document.createElementNS('http://www.w3.org/2000/svg','polyline');line.setAttribute('points',vals.map((v,i)=>`${i*1000/Math.max(1,vals.length-1)},${170-(v-lo)/(hi-lo)*160}`).join(' '));line.setAttribute('fill','none');line.setAttribute('stroke','#48d8bc');line.setAttribute('stroke-width','3');svg.append(line);
const b=s.backtest;document.getElementById('research').textContent='Sur '+b.strategy.observations+' séances après préchauffage : stratégie '+euro(b.strategy.liquidation_net)+' ; achat conservé SPY '+euro(b.passive.liquidation_net)+' (hypothèses identiques de frais et d’impôt, exposition différente).';
const tbody=document.getElementById('trades');tbody.replaceChildren();p.trades.slice(-20).reverse().forEach(t=>{const tr=document.createElement('tr');[t.date,t.side,t.symbol,t.amount.toFixed(2)].forEach(v=>{const td=document.createElement('td');td.textContent=v;tr.append(td)});tbody.append(tr)});
}catch(e){document.getElementById('status').textContent='Tableau de bord indisponible'}}refresh();setInterval(refresh,60000);
</script></html>'''


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            body, content = b'{"service":"up"}', 'application/json'
        elif self.path == '/api/status':
            with LOCK:
                body = json.dumps(STATE, allow_nan=False).encode()
            content = 'application/json'
        elif self.path == '/':
            body, content = PAGE.encode(), 'text/html; charset=utf-8'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', content)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    report = DATA/'report.json'
    if report.exists():
        STATE.update(json.loads(report.read_text()))
        STATE['status'] = 'Redémarrage — validation des données en cours'
    threading.Thread(target=worker, daemon=True).start()
    ThreadingHTTPServer(('0.0.0.0', 8080), Handler).serve_forever()

if __name__ == '__main__':
    main()
