import unittest
from datetime import date, timedelta
from bot.engine import simulate, Settings


def prices(n=500):
    return [dict(date=(date(2020,1,1)+timedelta(days=i)).isoformat(),
                 SPY=100+i, IEF=100., GLD=100.) for i in range(n)]


class EngineTest(unittest.TestCase):
    def test_signal_delay(self):
        rows = prices(201)
        rows[-1]['GLD'] = 100000
        r = simulate(rows)
        self.assertEqual(r['trades'][0]['symbol'], 'SPY')
        self.assertEqual(r['trades'][0]['date'], rows[200]['date'])

    def test_stop_is_permanent(self):
        rows = prices(230)
        rows[210]['SPY'] = 1
        r = simulate(rows)
        self.assertTrue(r['halted'])
        self.assertIsNone(r['holding'])
        self.assertEqual([t['side'] for t in r['trades']], ['BUY','SELL'])
        self.assertLess(r['max_drawdown'], -.2)  # Gaps can exceed requested limit.

    def test_cash_and_liquidation_costs(self):
        rows = prices(201)
        r = simulate(rows, Settings(tax_rate=0))
        self.assertAlmostEqual(r['curve'][0]['cash'], 5000)
        self.assertLess(r['liquidation_net'], 10000)

    def test_tax_on_liquidation(self):
        rows = prices()
        untaxed = simulate(rows, Settings(tax_rate=0))
        taxed = simulate(rows, Settings(tax_rate=.3))
        gain = untaxed['liquidation_net']-10000
        self.assertAlmostEqual(taxed['liquidation_net'], 10000+gain*.7, places=1)

    def test_no_future_rewrite(self):
        early = simulate(prices(300))
        late = simulate(prices(400))
        self.assertEqual(early['curve'], late['curve'][:100])
        self.assertEqual(early['trades'], [t for t in late['trades'] if t['date'] <= prices(300)[-1]['date']])

    def test_reject_duplicate_and_nan(self):
        rows = prices()
        rows[1] = rows[0]
        with self.assertRaises(ValueError): simulate(rows)
        rows = prices()
        rows[0]['SPY'] = float('nan')
        with self.assertRaises(ValueError): simulate(rows)

if __name__ == '__main__': unittest.main()
