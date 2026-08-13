import importlib.util
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("shadow_books_script", Path(__file__).parents[1] / "scripts" / "shadow_books.py")
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ShadowBookSelectionTests(unittest.TestCase):
    def test_pairs_same_selected_team_when_venue_order_differs(self):
        report = {
            "matches": [
                {
                    "kalshi": {
                        "event_id": "K-EVENT",
                        "contracts": [
                            {"selected_team": "A", "id": "K-A"},
                            {"selected_team": "B", "id": "K-B"},
                        ],
                    },
                    "polymarket": {
                        "contracts": [
                            {"selected_team": "B", "token_id": "P-B"},
                            {"selected_team": "A", "token_id": "P-A"},
                        ]
                    },
                }
            ]
        }
        self.assertEqual(
            MODULE.selected_pairs(report),
            [
                {
                    "event_id": "K-EVENT",
                    "team": "A",
                    "kalshi_contract_id": "K-A",
                    "polymarket_token_id": "P-A",
                },
                {
                    "event_id": "K-EVENT",
                    "team": "B",
                    "kalshi_contract_id": "K-B",
                    "polymarket_token_id": "P-B",
                },
            ],
        )

    def test_skips_unmatched_outcome_and_obeys_limit(self):
        report = {
            "matches": [
                {
                    "kalshi": {
                        "event_id": "K-EVENT",
                        "contracts": [
                            {"selected_team": "A", "id": "K-A"},
                            {"selected_team": "B", "id": "K-B"},
                        ],
                    },
                    "polymarket": {"contracts": [{"selected_team": "A", "token_id": "P-A"}]},
                }
            ]
        }
        self.assertEqual(len(MODULE.selected_pairs(report, limit=1)), 1)
        self.assertEqual(MODULE.selected_pairs(report, limit=1)[0]["team"], "A")


if __name__ == "__main__":
    unittest.main()
