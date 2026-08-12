import unittest
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

from arbs.domain import CanonicalContract, MaterialRules, NormalizedTime, Predicate, SourceEvidence
from arbs.matching.engine import candidate_pairs, complementary_binary, decide


def contract(venue="a", start="2026-08-12T17:40:00+00:00", outcome="BAL", rules_complete=True):
    rules = MaterialRules("MLB", "none", "included", "24h", "fair", "same-event-only", "team", "void",
                          "none", "review", "official", "UTC", "fair" if rules_complete else None)
    when = datetime.fromisoformat(start)
    return CanonicalContract(
        "1.0.0", "test", venue, venue+"-event", venue+"-contract", "baseball", "mlb", ("BAL", "MIN"),
        when, NormalizedTime(when, start, "+00:00"), "regular-season", (("BAL", "participant"), ("MIN", "participant")),
        False, None, Predicate("HEAD_TO_HEAD", "winner", "event", "full_game",
        "full_game_including_extras", "EQ", None, outcome), rules, "open", SourceEvidence(venue, venue+"-id", "https://example.com",
        "a"*64, "2026-08-12T00:00:00Z", ("title",), ("public",)))


class EngineTests(unittest.TestCase):
    def test_exact_requires_complete_equal_rules(self):
        a, b = contract(), contract("b")
        candidates = next(candidate_pairs([a], [b]))[1]
        result = decide(a, candidates)
        self.assertEqual(result.decision, "EXACT")
        self.assertTrue(result.pricing_eligible)

    def test_unknown_rule_is_review(self):
        a, b = contract(), contract("b", rules_complete=False)
        self.assertEqual(decide(a, (b,)).decision, "REVIEW")

    def test_predicate_difference_is_no_match(self):
        a, b = contract(), contract("b", outcome="MIN")
        self.assertEqual(decide(a, (b,)).decision, "NO_MATCH")

    def test_ambiguity_is_quarantined(self):
        a, b = contract(), contract("b")
        self.assertEqual(decide(a, (b, replace(b, contract_id="other"))).decision, "REVIEW")

    def test_consecutive_game_outside_window_not_candidate(self):
        a, b = contract(), contract("b", "2026-08-13T17:40:00+00:00")
        self.assertEqual(next(candidate_pairs([a], [b]))[1], ())

    def test_binary_complement_proof(self):
        self.assertTrue(complementary_binary(("BAL", "MIN"), ("MIN", "BAL")))
        self.assertFalse(complementary_binary(("BAL", "MIN"), ("BAL", "MIN", "DRAW")))


if __name__ == "__main__": unittest.main()
