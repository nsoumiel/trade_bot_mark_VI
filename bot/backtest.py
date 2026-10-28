"""python -m bot.backtest prices.csv ; prices must be in EUR, date,SPY,IEF,GLD."""
import argparse
import json
from .data import load_csv
from .engine import Settings, simulate

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv')
    parser.add_argument('--tax-rate', type=float, default=.30)
    args = parser.parse_args()
    rows = load_csv(args.csv)
    for name, passive in [('strategy', False), ('passive', True)]:
        report = simulate(rows, Settings(tax_rate=args.tax_rate), passive=passive)
        print(json.dumps({'scenario': name, **{k:v for k,v in report.items() if k not in ('curve','trades')}}, indent=2))
