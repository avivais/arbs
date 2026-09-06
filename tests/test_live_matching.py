import unittest
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from typing import Any, cast

from arbs.matching.live import (
    fetch_all_polymarket_events,
    match_events,
    normalize_kalshi,
    normalize_polymarket,
)


class LiveMatchingTests(unittest.TestCase):
    def setUp(self):
        self.kalshi = [
            {
                "ticker": f"KXMLBGAME-26AUG121907BOSTOR-{code}",
                "event_ticker": "KXMLBGAME-26AUG121907BOSTOR",
                "title": "Boston vs Toronto Winner?",
                "yes_sub_title": team,
                "status": "active",
                "rules_primary": f"If {team} wins the Boston vs Toronto professional baseball game originally scheduled for Aug 12, 2026 at 7:07 PM EDT, then the market resolves to Yes.",
                "rules_secondary": "If postponed over two days, resolve to a fair price.",
                "yes_bid_dollars": "0.4900",
                "yes_ask_dollars": "0.5100",
                "no_bid_dollars": "0.4900",
                "no_ask_dollars": "0.5100",
            }
            for code, team in (("BOS", "Boston"), ("TOR", "Toronto"))
        ]
        self.poly = [{
            "id": "805968", "slug": "bos-tor", "title": "Boston Red Sox vs. Toronto Blue Jays",
            "active": True, "closed": False, "endDate": "2026-08-12T23:07:00Z",
            "description": "If postponed, this market may resolve under Polymarket sports rules.",
            "markets": [{
                "id": "3379570", "question": "Boston Red Sox vs. Toronto Blue Jays",
                "active": True, "closed": False, "groupItemTitle": None,
                "gameStartTime": "2026-08-12 23:07:00+00",
                "outcomes": '["Boston Red Sox", "Toronto Blue Jays"]',
                "outcomePrices": '["0.53", "0.47"]',
                "clobTokenIds": '["token-bos", "token-tor"]',
                "bestBid": 0.52, "bestAsk": 0.54,
            }],
        }]

    def test_normalizes_and_matches_unique_event_as_review(self):
        kalshi = normalize_kalshi(self.kalshi)
        poly = normalize_polymarket(self.poly)
        self.assertEqual(len(kalshi), 1)
        self.assertEqual(len(poly), 1)
        self.assertEqual(kalshi[0].participants, ("BOS", "TOR"))
        self.assertEqual(
            kalshi[0].source_url,
            "https://kalshi.com/markets/kxmlbgame/professional-baseball-game/kxmlbgame-26aug121907bostor",
        )
        matches = match_events(kalshi, poly)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].decision, "REVIEW")
        self.assertFalse(matches[0].pricing_eligible)
        self.assertEqual(matches[0].start_delta_seconds, 0)
        self.assertIn("MATERIAL_RULE_EQUIVALENCE_NOT_PROVEN", matches[0].review_reasons)

    def test_normalizes_outcome_level_kalshi_titles_from_exact_contract_set(self):
        for market in self.kalshi:
            market["title"] = f"{market['yes_sub_title']} wins"
        normalized = normalize_kalshi(self.kalshi)
        self.assertEqual(len(normalized), 1)
        self.assertEqual(normalized[0].participants, ("BOS", "TOR"))

    def test_rejects_incomplete_or_unknown_kalshi_contract_set(self):
        self.kalshi[0]["title"] = "Boston wins"
        self.kalshi[1]["title"] = "Toronto wins"
        self.assertEqual(normalize_kalshi(self.kalshi[:1]), [])
        self.kalshi[1]["yes_sub_title"] = "Mystery Team"
        self.assertEqual(normalize_kalshi(self.kalshi), [])

    def test_rejects_start_outside_tolerance(self):
        self.poly[0]["markets"][0]["gameStartTime"] = "2026-08-13 00:00:00+00"
        self.assertEqual(match_events(normalize_kalshi(self.kalshi), normalize_polymarket(self.poly)), [])

    def test_rejects_unknown_team_alias(self):
        self.poly[0]["title"] = "Mystery Team vs. Toronto Blue Jays"
        self.assertEqual(normalize_polymarket(self.poly), [])

    def test_rejects_ambiguous_duplicate_candidate(self):
        duplicate = dict(self.poly[0])
        duplicate["id"] = "other"
        events = normalize_polymarket([self.poly[0], duplicate])
        self.assertEqual(match_events(normalize_kalshi(self.kalshi), events), [])

    def test_rejects_non_winner_polymarket_event(self):
        self.poly[0]["title"] += " - Player Props"
        self.assertEqual(normalize_polymarket(self.poly), [])

    def test_rejects_reverse_ambiguous_kalshi_candidates(self):
        kalshi = normalize_kalshi(self.kalshi)
        other = replace(kalshi[0], event_id="other-game")
        for events in ([kalshi[0], other], [other, kalshi[0]]):
            self.assertEqual(match_events(iter(events), normalize_polymarket(self.poly)), [])

    def test_rejects_malformed_polymarket_outcome_arrays(self):
        for field, value in (
            ("outcomes", '["Boston Red Sox", "Toronto Blue Jays", "Boston Red Sox"]'),
            ("outcomePrices", '[]'),
            ("outcomePrices", 'null'),
            ("clobTokenIds", '["same", "same"]'),
            ("outcomes", '{"Boston Red Sox": 1, "Toronto Blue Jays": 2}'),
        ):
            with self.subTest(field=field, value=value):
                events = deepcopy(self.poly)
                events[0]["markets"][0][field] = value
                self.assertEqual(normalize_polymarket(events), [])

    def test_tolerance_does_not_truncate_fractional_seconds(self):
        kalshi = normalize_kalshi(self.kalshi)
        poly = normalize_polymarket(self.poly)
        at_boundary = replace(poly[0], start_utc=kalshi[0].start_utc + timedelta(seconds=900))
        self.assertEqual(len(match_events(kalshi, [at_boundary])), 1)
        outside = replace(at_boundary, start_utc=at_boundary.start_utc + timedelta(microseconds=1))
        self.assertEqual(match_events(kalshi, [outside]), [])

    def test_rescheduled_slug_is_not_an_identity_veto_or_eligibility_override(self):
        # A stale slug can describe the original date of a real makeup game.
        self.poly[0]["slug"] = "mlb-bos-tor-2026-06-06"
        matches = match_events(normalize_kalshi(self.kalshi), normalize_polymarket(self.poly))
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].decision, "REVIEW")
        self.assertFalse(matches[0].pricing_eligible)

    def test_pagination_repeated_cursor_and_page_bound_fail_closed(self):
        class Client:
            def list_sports_events(self, tag_id, *, limit, after_cursor):
                return SimpleNamespace(data={"events": [], "next_cursor": "repeat"})
        with self.assertRaisesRegex(RuntimeError, "repeated a cursor"):
            fetch_all_polymarket_events(cast(Any, Client()))
        with self.assertRaisesRegex(RuntimeError, "exceeded safety bound"):
            fetch_all_polymarket_events(cast(Any, Client()), max_pages=1)

    def test_live_discovery_uses_small_bounded_pages_without_losing_pagination(self):
        class Client:
            def __init__(self):
                self.calls = []

            def list_sports_events(self, tag_id, *, limit, after_cursor):
                self.calls.append((tag_id, limit, after_cursor))
                if after_cursor is None:
                    return SimpleNamespace(data={"events": [{"id": "first"}], "next_cursor": "next"})
                return SimpleNamespace(data={"events": [{"id": "second"}], "next_cursor": ""})

        client = Client()
        self.assertEqual(
            [row["id"] for row in fetch_all_polymarket_events(cast(Any, client))],
            ["first", "second"],
        )
        self.assertEqual(client.calls, [(100381, 10, None), (100381, 10, "next")])


if __name__ == "__main__":
    unittest.main()
