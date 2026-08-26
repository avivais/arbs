import unittest

from arbs.matching.live import match_events, normalize_kalshi, normalize_polymarket


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


if __name__ == "__main__":
    unittest.main()
