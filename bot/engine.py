"""Daily paper execution. Signals use yesterday's close; execution uses today's close."""
from dataclasses import dataclass, asdict
from datetime import date
import math

SYMBOLS = ('SPY', 'IEF', 'GLD')

@dataclass
class Settings:
    capital: float = 10000
    allocation: float = 0.5
    fee: float = 1
    slippage: float = 0.001
    tax_rate: float = 0.30  # Scenario assumption, not a statement of current law.
    stop: float = 0.15

    def __post_init__(self):
        if not (self.capital > 0 and 0 < self.allocation <= 1 and
                self.fee >= 0 and 0 <= self.slippage < 1 and
                0 <= self.tax_rate <= 1 and 0 < self.stop <= 1):
            raise ValueError('Paramètres hors limites')


def validate(rows):
    previous = None
    for row in rows:
        day = date.fromisoformat(row['date'])
        if previous and day <= previous:
            raise ValueError('Dates non croissantes ou dupliquées')
        previous = day
        for symbol in SYMBOLS:
            if not math.isfinite(row[symbol]) or row[symbol] <= 0:
                raise ValueError('Prix non positif ou non fini')


def simulate(rows, config=None, passive=False):
    cfg = config or Settings()
    validate(rows)
    cash, units, cost = cfg.capital, 0., 0.
    holding, last_month = None, None
    peak, halted, worst = cfg.capital, False, 0.
    trades, curve, losses = [], [], []
    annual_gain, tax_paid, year = 0., 0., None

    def sell(row):
        nonlocal cash, units, cost, holding, annual_gain
        if holding:
            proceeds = units * row[holding] * (1-cfg.slippage) - cfg.fee
            gain = proceeds-cost
            cash += proceeds
            annual_gain += gain
            trades.append(dict(date=row['date'], side='SELL', symbol=holding,
                               units=units, amount=proceeds, gain=gain))
            holding, units, cost = None, 0., 0.

    def reserve_tax(current_year):
        nonlocal cash, annual_gain, tax_paid, losses
        losses = [(y, n) for y, n in losses if current_year-y <= 10]
        taxable = max(0., annual_gain)
        for i, (y, n) in enumerate(losses):
            used = min(n, taxable)
            taxable -= used
            losses[i] = (y, n-used)
        if annual_gain < 0:
            losses.append((current_year, -annual_gain))
        tax = taxable * cfg.tax_rate
        cash -= tax
        tax_paid += tax
        annual_gain = 0.

    for i in range(200, len(rows)):
        row, yesterday = rows[i], rows[i-1]
        current_year = int(row['date'][:4])
        if year is not None and year != current_year:
            reserve_tax(year)
        year = current_year
        equity = cash + (units*row[holding] if holding else 0.)
        # Reserve the estimated current-year tax even before cash payment.
        credit = sum(n for y, n in losses if current_year-y <= 10)
        liability = max(0., annual_gain-credit)*cfg.tax_rate
        net = equity-liability
        peak = max(peak, net)
        drawdown = net/peak-1
        worst = min(worst, drawdown)
        # A permanent halt requires a deliberate strategy review to change settings.
        if not passive and drawdown <= -cfg.stop:
            halted = True
            sell(row)
        month = row['date'][:7]
        if not halted and (month != last_month or (passive and holding is None)):
            target = 'SPY' if passive else None
            if not passive:
                eligible = []
                for symbol in SYMBOLS:
                    avg = sum(r[symbol] for r in rows[i-200:i])/200
                    momentum = yesterday[symbol]/rows[i-64][symbol]-1
                    if yesterday[symbol] > avg and momentum > 0:
                        eligible.append((momentum, symbol))
                target = max(eligible)[1] if eligible else None
            if target != holding:
                sell(row)
                liability = max(0., annual_gain-credit)*cfg.tax_rate
                budget = max(0., cash-liability)*(1 if passive else cfg.allocation)
                if target and budget > cfg.fee:
                    units = (budget-cfg.fee)/(row[target]*(1+cfg.slippage))
                    cash -= budget
                    cost, holding = budget, target
                    trades.append(dict(date=row['date'], side='BUY', symbol=target,
                                       units=units, amount=budget))
            last_month = month
        liability = max(0., annual_gain-credit)*cfg.tax_rate
        equity = cash+(units*row[holding] if holding else 0.)
        net = equity-liability
        peak = max(peak, net)
        worst = min(worst, net/peak-1)
        curve.append(dict(date=row['date'], gross=round(equity, 2),
                          net=round(net, 2), cash=round(cash, 2)))
    liquidation = cash
    if holding and rows:
        liquidation += units*rows[-1][holding]*(1-cfg.slippage)-cfg.fee
        annual_gain += units*rows[-1][holding]*(1-cfg.slippage)-cfg.fee-cost
    credit = sum(n for y, n in losses if year is not None and year-y <= 10)
    liquidation -= max(0., annual_gain-credit)*cfg.tax_rate
    return dict(settings=asdict(cfg), observations=len(curve), curve=curve,
                trades=trades, holding=holding, units=units, halted=halted,
                tax_paid=round(tax_paid, 2), max_drawdown=round(worst, 4),
                liquidation_net=round(liquidation, 2),
                return_net=round(liquidation/cfg.capital-1, 4))
