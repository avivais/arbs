"""Fixed offline replay/rounding tests; never reads rolling data or the network."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
import importlib.util
from pathlib import Path
import unittest
import json
import hashlib
import tempfile

from arbs.pricing import normalize_levels
from arbs.venue_fees import FeeFill, quote_fees
from test_venue_fees import schedule

D = Decimal
spec = importlib.util.spec_from_file_location('replay_fee', Path(__file__).resolve().parents[1]/'scripts/replay_fee_candidates.py')
replay_fee = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay_fee)


class FeeReplayTests(unittest.TestCase):
    def test_walks_asks_and_fails_without_depth(self):
        levels = normalize_levels([('0.4','5'),('0.6','5')])
        fills = replay_fee.depth_fills(levels,D('10'))
        self.assertEqual(sum(f.price*f.quantity for f in fills),D('5'))
        with self.assertRaises(ValueError):
            replay_fee.depth_fills(levels,D('11'))
        with self.assertRaises(ValueError):
            replay_fee.depth_fills(levels,D('10'),adverse=D('.5'))

    def test_adverse_fallback_costs_more(self):
        levels = normalize_levels([('0.4','5'),('0.6','5')])
        normal = replay_fee.depth_fills(levels,D('5'))
        adverse = replay_fee.depth_fills(levels,D('5'),adverse=D('.02'))
        self.assertGreater(sum(f.price*f.quantity for f in adverse),sum(f.price*f.quantity for f in normal))
        after_consumed = replay_fee.depth_fills(levels,D('5'),skip=D('5'))
        self.assertEqual(after_consumed,[FeeFill(D('.6'),D('5'))])

    def test_rounding_uses_revenue_grid_not_just_fee_cent(self):
        # Official non-direct worked example: -0.055 revenue, .00363825 fee.
        # Curve chosen to reproduce that raw fee: rate * qty * p*(1-p).
        from arbs.venue_fees import kalshi_fee_upper_bound
        self.assertEqual(kalshi_fee_upper_bound(D('.00363825'),D('.055'),D('.01')),D('.005'))

    def test_multiplier_and_no_accumulator_credit(self):
        model = schedule(multiplier=D('.5'))
        q = quote_fees(model,[FeeFill(D('.5'),D('100'))],as_of=date(2026,9,17))
        self.assertEqual(q.fills[0].raw_fee,D('.875'))
        self.assertFalse(q.exact_venue_fee)
        self.assertEqual(q.guaranteed_rebate,D('0'))
        with self.assertRaises(ValueError):
            replace(model,multiplier=D('-1'))

    def test_offline_replay_is_deterministic_closed_and_hash_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'sources').mkdir()
            row={'event_id':'TEST', 'legs':[
                {'venue':v,'instrument_id':i,'outcome':'X',
                 'ask_levels':[{'price':'.4','quantity':'20'}],
                 'received_at':'2026-09-17T00:00:00Z',
                 'source_time_status':'not_exposed','source_age_at_receipt_ms':None}
                for v,i in [('kalshi','TEST-YES'),('polymarket','123')]]}
            snapshot={'generated_at':'2026-09-17T00:00:01Z','records':[row]}
            (root/'indicators-input.json').write_text(json.dumps(snapshot))
            payloads={'kalshi-series':{'series':{'fee_multiplier':.5}},
                      'polymarket-fees':{'test':'synthetic'},
                      'poly-market-00':[{'id':'m','clobTokenIds':'["123","456"]',
                         'feesEnabled':True,'feeSchedule':{'rate':.05,'exponent':1,'takerOnly':True},
                         'orderMinSize':5}],
                      'kalshi-event-TEST':{'event_fee_changes':[]}}
            sources={}
            for key,value in payloads.items():
                path=root/'sources'/(key+'.capture')
                path.write_text(json.dumps(value))
                sources[key]={'path':str(path),'sha256':replay_fee.digest(path),
                              'url':'https://example.invalid/synthetic',
                              'retrieved_at':'2026-09-17T00:01:00Z','status':200}
            manifest={'sources':sources,'input_sha256':replay_fee.digest(root/'indicators-input.json')}
            (root/'source-manifest.json').write_text(json.dumps(manifest))
            a=replay_fee.replay(root,1)
            self.assertEqual(a,replay_fee.replay(root,1))
            self.assertEqual(a['path_count'],6)
            self.assertEqual(a['conditional_arithmetic_count'],6)
            for result in a['results']:
                self.assertFalse(result['pricing_eligible'])
                self.assertIsNone(result['net_profit'])
                self.assertFalse(result['maker_fill_guaranteed'])
                self.assertIn('OTHER_COST_INPUTS_MISSING',result['blockers'])
            (root/'sources/polymarket-fees.capture').write_text('tampered')
            with self.assertRaisesRegex(ValueError,'source hash changed'):
                replay_fee.replay(root,1)

    def test_missing_effective_date_stays_conditional(self):
        q=quote_fees(schedule(effective_date=None),[FeeFill(D('.5'),D('10'))],
                     as_of=date(2026,9,17),allow_conditional=True)
        self.assertFalse(q.verified)
        self.assertIn('UNKNOWN_EFFECTIVE_DATE',q.blockers)

if __name__ == '__main__':
    unittest.main()
