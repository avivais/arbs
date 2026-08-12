import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from arbs.domain import decimal_exact, utc_exact
from arbs.pricing import Book, FeeModel, Level, common_depth, price_pair, walk


class DomainAndPricingTests(unittest.TestCase):
    def test_exact_parsing(self):
        self.assertEqual(decimal_exact("0.10"), Decimal("0.10"))
        self.assertEqual(utc_exact("2026-08-12T17:40:00-04:00").isoformat(), "2026-08-12T21:40:00+00:00")
        with self.assertRaises(ValueError): decimal_exact(0.1)
        with self.assertRaises(ValueError): utc_exact("2026-08-12T17:40:00")

    def test_depth_walk_and_common_quantity(self):
        now = datetime.now(timezone.utc)
        a = Book("a", "1", "A", (Level(Decimal("0.40"), Decimal("2")), Level(Decimal("0.50"), Decimal("3"))), now)
        b = Book("b", "2", "B", (Level(Decimal("0.40"), Decimal("4")),), now)
        self.assertEqual(common_depth(a, b), Decimal("4"))
        fill = walk(a.asks, Decimal("4"))
        self.assertEqual(fill.cost, Decimal("1.80"))
        self.assertEqual(fill.vwap, Decimal("0.45"))

    def test_profitable_pair_after_fees_and_buffer(self):
        now = datetime.now(timezone.utc)
        a = Book("a", "1", "A", (Level(Decimal("0.40"), Decimal("10")),), now)
        b = Book("b", "2", "B", (Level(Decimal("0.45"), Decimal("10")),), now)
        result = price_pair(a, b, semantic_pricing_eligible=True, now=now, max_age_ms=1000, max_skew_ms=1000,
                            first_fee=FeeModel(Decimal("0.01")), second_fee=FeeModel(Decimal("0.01")),
                            safety_buffer_per_contract=Decimal("0.01"), quantity=Decimal("5"))
        self.assertTrue(result.eligible)
        self.assertEqual(result.net_profit, Decimal("0.6575"))

    def test_semantic_review_always_blocks_pricing(self):
        now = datetime.now(timezone.utc)
        book = Book("a", "1", "A", (Level(Decimal("0.10"), Decimal("10")),), now)
        result = price_pair(book, book, semantic_pricing_eligible=False, now=now, max_age_ms=1000, max_skew_ms=1000,
                            first_fee=FeeModel(Decimal("0")), second_fee=FeeModel(Decimal("0")),
                            safety_buffer_per_contract=Decimal("0"))
        self.assertFalse(result.eligible)
        self.assertEqual(result.reason, "SEMANTIC_MATCH_NOT_PRICING_ELIGIBLE")

    def test_stale_and_skewed_books_are_blocked(self):
        now = datetime.now(timezone.utc)
        old = Book("a", "1", "A", (Level(Decimal("0.10"), Decimal("10")),), now - timedelta(seconds=2))
        fresh = Book("b", "2", "B", (Level(Decimal("0.10"), Decimal("10")),), now)
        kwargs = dict(semantic_pricing_eligible=True, now=now, max_age_ms=1000, max_skew_ms=500,
                      first_fee=FeeModel(Decimal("0")), second_fee=FeeModel(Decimal("0")),
                      safety_buffer_per_contract=Decimal("0"))
        self.assertEqual(price_pair(old, fresh, **kwargs).reason, "STALE_BOOK")

    def test_fees_and_less_depth_cannot_improve_result(self):
        now = datetime.now(timezone.utc)
        a = Book("a", "1", "A", (Level(Decimal("0.40"), Decimal("10")),), now)
        b = Book("b", "2", "B", (Level(Decimal("0.45"), Decimal("10")),), now)
        base = dict(semantic_pricing_eligible=True, now=now, max_age_ms=1000, max_skew_ms=1000,
                    safety_buffer_per_contract=Decimal("0"), quantity=Decimal("5"))
        no_fee = price_pair(a, b, first_fee=FeeModel(Decimal("0")), second_fee=FeeModel(Decimal("0")), **base)
        fee = price_pair(a, b, first_fee=FeeModel(Decimal("0.02")), second_fee=FeeModel(Decimal("0.02")), **base)
        self.assertLessEqual(fee.net_profit, no_fee.net_profit)
        shallow = Book("b", "2", "B", (Level(Decimal("0.45"), Decimal("2")),), now)
        self.assertLessEqual(common_depth(a, shallow), common_depth(a, b))


if __name__ == "__main__": unittest.main()
