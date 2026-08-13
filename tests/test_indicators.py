import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from arbs.indicators import IndicatorLeg, evaluate_candidate, kalshi_yes_asks, polymarket_asks
from arbs.pricing import Level


class IndicatorTests(unittest.TestCase):
    def leg(self, venue, outcome, asks, at=None):
        return IndicatorLeg(venue, outcome, venue + outcome, tuple(Level(Decimal(p), Decimal(q)) for p, q in asks), at or datetime.now(timezone.utc))

    def test_extracts_executable_asks_from_venue_payloads(self):
        sample = {
            "status": "complete",
            "kalshi": {"payload": {"orderbook_fp": {"no_dollars": [["0.60", "3"], ["0.55", "4"]]}}},
            "polymarket": {"payload": {"asks": [{"price": "0.42", "size": "2"}, {"price": "0.41", "size": "1"}]}}
        }
        self.assertEqual([(x.price, x.quantity) for x in kalshi_yes_asks(sample)], [(Decimal("0.40"), Decimal("3")), (Decimal("0.45"), Decimal("4"))])
        self.assertEqual([x.price for x in polymarket_asks(sample)], [Decimal("0.41"), Decimal("0.42")])

    def test_walks_maximum_depth_surviving_reserve(self):
        now = datetime.now(timezone.utc)
        a = self.leg("kalshi", "A", [("0.40", "2"), ("0.44", "3")], now)
        b = self.leg("polymarket", "B", [("0.50", "4"), ("0.57", "4")], now)
        result = evaluate_candidate(a, b, now=now, reserve_per_pair=Decimal("0.01"))
        self.assertEqual(result.status, "BUFFERED_CANDIDATE")
        self.assertEqual(result.quantity, Decimal("4"))
        self.assertEqual(result.total_cost, Decimal("3.68"))
        self.assertEqual(result.gross_profit, Decimal("0.32"))
        self.assertEqual(result.provisional_profit, Decimal("0.28"))

    def test_separates_gross_only_from_no_edge(self):
        now = datetime.now(timezone.utc)
        first = self.leg("kalshi", "A", [("0.495", "2")], now)
        gross_only = self.leg("polymarket", "B", [("0.500", "2")], now)
        no_edge = self.leg("polymarket", "B", [("0.505", "2")], now)
        self.assertEqual(evaluate_candidate(first, gross_only, now=now).status, "GROSS_ONLY")
        self.assertEqual(evaluate_candidate(first, no_edge, now=now).status, "NO_EDGE")

    def test_stale_gross_only_is_not_presented_as_current(self):
        now = datetime.now(timezone.utc)
        first = self.leg("kalshi", "A", [("0.495", "2")], now - timedelta(seconds=91))
        second = self.leg("polymarket", "B", [("0.500", "2")], now - timedelta(seconds=91))
        self.assertEqual(evaluate_candidate(first, second, now=now).status, "STALE_OR_SKEWED")

    def test_reports_cross_leg_skew_and_age(self):
        now = datetime.now(timezone.utc)
        first = self.leg("kalshi", "A", [("0.4", "1")], now - timedelta(seconds=93))
        second = self.leg("polymarket", "B", [("0.5", "1")], now - timedelta(seconds=92))
        result = evaluate_candidate(first, second, now=now)
        self.assertEqual(result.quote_age_ms, 93000)
        self.assertEqual(result.pair_skew_ms, 1000)
        self.assertEqual(result.status, "STALE_OR_SKEWED")

    def test_fresh_buffered_candidate_remains_actionable_indicator(self):
        now = datetime.now(timezone.utc)
        first = self.leg("kalshi", "A", [("0.4", "1")], now)
        second = self.leg("polymarket", "B", [("0.5", "1")], now)
        self.assertEqual(evaluate_candidate(first, second, now=now).status, "BUFFERED_CANDIDATE")


if __name__ == "__main__":
    unittest.main()
