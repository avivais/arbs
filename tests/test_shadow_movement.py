import json
import tempfile
import unittest
from pathlib import Path

from arbs.shadow_movement import report


class MovementTests(unittest.TestCase):
    def test_bounded_samples_produce_transitions_without_eligibility(self):
        # Never enumerate the growing live corpus in the unit quality gate.
        def sample(pair, minute, bid="0.40", digest="same"):
            return {
                "status": "complete", "pair_id": pair,
                "started_at": f"2026-08-12T00:0{minute}:00Z",
                "kalshi": {"payload_sha256": digest, "payload": {
                    "orderbook_fp": {"yes_dollars": [[bid, "10"]], "no_dollars": [["0.50", "10"]]}}},
                "polymarket": {"payload_sha256": "same", "payload": {
                    "bids": [{"price": "0.39", "size": "10"}],
                    "asks": [{"price": "0.51", "size": "10"}]}},
            }

        rows = [sample("a", 0), sample("b", 1), {"status": "failed"},
                sample("a", 3), sample("a", 4, digest="depth-only"),
                sample("a", 5, bid="0.41", digest="top-changed")]
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for i, row in enumerate(rows):
                path = Path(directory) / f"20260812T000{i}00Z.json"
                path.write_text(json.dumps(row))
                paths.append(path)
            detailed = report(list(reversed(paths)))
            compact = report(paths, include_transitions=False)
        self.assertEqual(compact, {"schema_version": 1, "pair_count": 2,
                                  "successful_samples": 5, "failure_count": 1,
                                  "transition_count": 3, "changed_transition_count": 2,
                                  "top_quote_changed_transition_count": 1, "transitions": []})
        self.assertEqual({k: v for k, v in detailed.items() if k != "transitions"},
                         {k: v for k, v in compact.items() if k != "transitions"})
        self.assertEqual(len(detailed["transitions"]), 3)
        self.assertEqual(detailed["transitions"][-1]["venues"]["kalshi"]["bid_after"], "0.41")
        self.assertEqual(detailed["transitions"][0]["before"], "2026-08-12T00:00:00Z")
        self.assertNotIn("pricing_eligible", json.dumps(detailed))

    def test_empty_evidence_has_no_transitions(self):
        value = report([])
        self.assertEqual(value["successful_samples"], 0)
        self.assertEqual(value["transition_count"], 0)
        self.assertEqual(value["transitions"], [])


if __name__ == "__main__":
    unittest.main()
