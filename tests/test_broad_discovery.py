import copy
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import unittest
from arbs.candidate_discovery import build_proposals, verify_proposal, DIMENSIONS
from arbs.discovery_review import fingerprint, validate_reviews, attach_reviews
from arbs.broad_pricing import evaluate_proposals
from arbs.pricing import Book, Level, FeeModel


def market(venue, title='Will Bitcoin exceed 100000 in December 2026?'):
    return {'venue': venue, 'id': venue + '-fixture', 'title': title, 'category': 'crypto',
            'description': '', 'rules': 'Official fixture rule. Exceptions unresolved.',
            'close_time': '2026-12-31T00:00:00Z', 'outcomes': ['Yes', 'No'], 'url': 'https://example.com'}


def proposal():
    return build_proposals([market('kalshi'), market('polymarket')])[0]


def review(p):
    return {'id': p['id'], 'left_fingerprint': fingerprint(p['left']), 'right_fingerprint': fingerprint(p['right']),
            'verdict': 'REVIEW', 'orientation': 'same', 'reason': 'Titles overlap but exceptional settlement remains unresolved.',
            'differences': ['Exceptions unverified'], 'left_excerpt': p['left']['title'], 'right_excerpt': p['right']['title']}


class CandidateReviewTests(unittest.TestCase):
    def test_alias_retrieval_and_no_promotion(self):
        ps = build_proposals([market('kalshi'), market('polymarket', 'BTC above 100000 December 2026?')])
        self.assertEqual(len(ps), 1)
        self.assertFalse(ps[0]['pricing_eligible'])
        self.assertEqual(ps[0]['verification']['exceptions']['status'], 'MISSING')

    def test_explicit_threshold_mismatch(self):
        p = proposal()
        p['left']['semantic_fields'] = {'threshold': 100000}
        p['right']['semantic_fields'] = {'threshold': 110000}
        self.assertEqual(verify_proposal(p)['status'], 'REJECT')

    def test_unrelated_not_matched(self):
        self.assertEqual(build_proposals([market('kalshi'), market('polymarket', 'Will France elect a new president?')]), [])

    def test_ai_cannot_approve_or_invent_evidence(self):
        p = proposal()
        r = review(p)
        for key, value in [('verdict', 'EXACT'), ('left_excerpt', 'invented source quote'), ('right_fingerprint', 'wrong')]:
            bad = dict(r, **{key: value})
            with self.assertRaises(ValueError):
                validate_reviews({'reviews': [bad]}, [p])

    def test_review_apply_and_invalidate_on_rule_change(self):
        p = proposal()
        rows = validate_reviews({'reviews': [review(p)]}, [p])
        self.assertIn('ai_review', attach_reviews([copy.deepcopy(p)], rows)[0])
        p['left']['rules'] += ' Revised.'
        self.assertNotIn('ai_review', attach_reviews([p], rows)[0])

    def test_ai_rejection_is_not_overridden(self):
        p = proposal()
        r = dict(review(p), verdict='REJECT')
        row = attach_reviews([p], validate_reviews({'reviews': [r]}, [p]))[0]
        self.assertEqual(row['status'], 'REJECT')
        self.assertFalse(row['pricing_eligible'])

    def test_duplicate_reviews_fail(self):
        p = proposal()
        with self.assertRaises(ValueError):
            validate_reviews({'reviews': [review(p), review(p)]}, [p])

    def test_no_cross_category_match_without_other(self):
        a, b = market('kalshi'), market('polymarket')
        b['category'] = 'politics'
        self.assertEqual(build_proposals([a, b]), [])


class BroadPricingTests(unittest.TestCase):
    def setUp(self):
        self.p = proposal()
        self.now = datetime.now(timezone.utc)
        self.approval = {'reviewer_type': 'independent_policy_review', 'version': 'fixture-only-1',
            'evidence_url': 'https://example.com/fixture', 'orientation': 'same',
            'left_fingerprint': fingerprint(self.p['left']), 'right_fingerprint': fingerprint(self.p['right']),
            'checks': dict.fromkeys(DIMENSIONS, True),
            'fees': {'left': FeeModel(Decimal('0.01')), 'right': FeeModel(Decimal('0.01'))}}

    def quotes(self, m, outcome):
        return Book(m['venue'], m['id'], outcome, (Level(Decimal('0.40'), Decimal('10')),), self.now)

    def run_pricing(self, approval=None, provider=None):
        return evaluate_proposals([self.p], approvals={self.p['id']: self.approval if approval is None else approval},
                                  quote_provider=provider or self.quotes, now=self.now)['results'][0]

    def test_default_never_fetches_quotes(self):
        result = evaluate_proposals([dict(self.p, pricing_eligible=True)], quote_provider=lambda *_: self.fail('called'))
        self.assertEqual(result['evaluable'], 0)
        self.assertFalse(result['results'][0]['eligible'])

    def test_synthetic_all_cost_depth_calculation(self):
        r = self.run_pricing()
        self.assertTrue(r['eligible'])
        self.assertEqual(r['net_profit'], '0.1820')

    def test_ai_policy_not_accepted(self):
        self.assertFalse(self.run_pricing(dict(self.approval, reviewer_type='AI'))['eligible'])

    def test_missing_fees_rejected(self):
        self.assertEqual(self.run_pricing(dict(self.approval, fees={}))['reason'], 'REVIEWED_FEE_MODEL_REQUIRED')

    def test_changed_rules_rejected(self):
        self.p['left']['rules'] += ' changed'
        self.assertFalse(self.run_pricing()['eligible'])

    def test_future_quote_rejected(self):
        def quotes(m, outcome):
            return Book(m['venue'], m['id'], outcome, (Level(Decimal('.4'), Decimal(1)),), self.now + timedelta(seconds=1))
        self.assertIn('QUOTE_VALIDATION_FAILED', self.run_pricing(provider=quotes)['reason'])

    def test_stale_quote_rejected(self):
        def quotes(m, outcome):
            return Book(m['venue'], m['id'], outcome, (Level(Decimal('.4'), Decimal(1)),), self.now - timedelta(seconds=60))
        self.assertEqual(self.run_pricing(provider=quotes)['reason'], 'STALE_BOOK')

    def test_reversed_buys_yes_yes(self):
        seen = []
        def quotes(m, outcome):
            seen.append(outcome)
            return self.quotes(m, outcome)
        self.assertTrue(self.run_pricing(dict(self.approval, orientation='reversed'), quotes)['eligible'])
        self.assertEqual(seen, ['Yes', 'Yes'])

    def test_outcome_identity_fails_closed(self):
        def quotes(m, outcome):
            return Book(m['venue'], m['id'], 'wrong', (Level(Decimal('.4'), Decimal(1)),), self.now)
        self.assertFalse(self.run_pricing(provider=quotes)['eligible'])

    def test_negative_fees_rejected(self):
        bad = dict(self.approval, fees={'left': FeeModel(Decimal('-1')), 'right': FeeModel(Decimal('0'))})
        self.assertFalse(self.run_pricing(bad)['eligible'])
